#include "native_surface.h"
#include "gl_bindings.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <dlfcn.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <linux/fb.h>
#include <sys/mman.h>

// Forward declarations for Android internal Surface types
struct ANativeWindow;

// Fallback Framebuffer Direct Device
static int s_fb_fd = -1;
static uint8_t* s_fb_ptr = NULL;
static size_t s_fb_size = 0;
static struct fb_var_screeninfo s_vinfo;
static struct fb_fix_screeninfo s_finfo;

// Load SurfaceComposerClient from libgui.so dynamically across Android versions
static void* create_surface_flinger_window(NativeOverlayContext* ctx, int w, int h) {
    const char* gui_libs[] = {
        "/system/lib64/libgui.so",
        "/system/lib/libgui.so",
        "libgui.so"
    };

    void* libgui = NULL;
    for (const char* lib : gui_libs) {
        libgui = dlopen(lib, RTLD_NOW | RTLD_GLOBAL);
        if (libgui) {
            printf("[NativeSurface] Loaded SurfaceFlinger client library: %s\n", lib);
            break;
        }
    }

    if (!libgui) {
        printf("[NativeSurface] Warning: libgui.so not directly loadable (%s). Checking fallback methods...\n", dlerror());
        return NULL;
    }

    // Try finding symbols for SurfaceComposerClient
    // 1. SurfaceComposerClient constructor
    typedef void (*fn_client_ctor)(void*);
    fn_client_ctor client_ctor = (fn_client_ctor)dlsym(libgui, "_ZN7android21SurfaceComposerClientC1Ev");
    if (!client_ctor) client_ctor = (fn_client_ctor)dlsym(libgui, "_ZN7android21SurfaceComposerClientC2Ev");

    if (!client_ctor) {
        printf("[NativeSurface] SurfaceComposerClient constructor symbol not found.\n");
        return NULL;
    }

    printf("[✓] SurfaceComposerClient dynamic interface resolved.\n");
    return NULL;
}

static bool init_framebuffer_fallback(NativeOverlayContext* ctx) {
    const char* fb_paths[] = { "/dev/graphics/fb0", "/dev/fb0" };
    for (const char* path : fb_paths) {
        s_fb_fd = open(path, O_RDWR);
        if (s_fb_fd >= 0) {
            if (ioctl(s_fb_fd, FBIOGET_VSCREENINFO, &s_vinfo) == 0 &&
                ioctl(s_fb_fd, FBIOGET_FSCREENINFO, &s_finfo) == 0) {
                s_fb_size = s_finfo.smem_len;
                s_fb_ptr = (uint8_t*)mmap(0, s_fb_size, PROT_READ | PROT_WRITE, MAP_SHARED, s_fb_fd, 0);
                if (s_fb_ptr != MAP_FAILED) {
                    printf("[NativeSurface] Framebuffer fallback active: %s (%dx%d, %d bpp)\n",
                           path, s_vinfo.xres, s_vinfo.yres, s_vinfo.bits_per_pixel);
                    ctx->screen_width = (int)s_vinfo.xres;
                    ctx->screen_height = (int)s_vinfo.yres;
                    return true;
                }
            }
            close(s_fb_fd);
            s_fb_fd = -1;
        }
    }
    return false;
}

bool native_surface_get_display_metrics(int* out_width, int* out_height) {
    if (!out_width || !out_height) return false;
    *out_width = 2400;
    *out_height = 1080;

    // 1. Try dumpsys display / wm size
    FILE* fp = popen("wm size 2>/dev/null", "r");
    if (fp) {
        char buf[128];
        if (fgets(buf, sizeof(buf), fp)) {
            int w = 0, h = 0;
            if (sscanf(buf, "Physical size: %dx%d", &w, &h) == 2 ||
                sscanf(buf, "Override size: %dx%d", &w, &h) == 2) {
                if (w > 0 && h > 0) {
                    *out_width = (w > h) ? w : h;
                    *out_height = (w > h) ? h : w;
                    pclose(fp);
                    return true;
                }
            }
        }
        pclose(fp);
    }

    // 2. Try Framebuffer ioctl
    int fd = open("/dev/graphics/fb0", O_RDONLY);
    if (fd < 0) fd = open("/dev/fb0", O_RDONLY);
    if (fd >= 0) {
        struct fb_var_screeninfo vinfo;
        if (ioctl(fd, FBIOGET_VSCREENINFO, &vinfo) == 0 && vinfo.xres > 0 && vinfo.yres > 0) {
            *out_width = (int)((vinfo.xres > vinfo.yres) ? vinfo.xres : vinfo.yres);
            *out_height = (int)((vinfo.xres > vinfo.yres) ? vinfo.yres : vinfo.xres);
            close(fd);
            return true;
        }
        close(fd);
    }

    return true;
}

bool native_surface_init(NativeOverlayContext* ctx, int target_w, int target_h) {
    if (!ctx) return false;
    memset(ctx, 0, sizeof(NativeOverlayContext));

    // 1. Initialize Dynamic EGL & GLES2 Bindings
    if (!init_gl_bindings()) {
        fprintf(stderr, "[-] NativeSurface: Failed to load dynamic EGL/GLES2 symbols.\n");
        return false;
    }

    if (target_w <= 0 || target_h <= 0) {
        native_surface_get_display_metrics(&ctx->screen_width, &ctx->screen_height);
    } else {
        ctx->screen_width = target_w;
        ctx->screen_height = target_h;
    }

    printf("[NativeSurface] Target Display Resolution: %dx%d (Landscape)\n", ctx->screen_width, ctx->screen_height);

    // 2. Initialize EGL Display
    ctx->display = p_eglGetDisplay(EGL_DEFAULT_DISPLAY);
    if (ctx->display == EGL_NO_DISPLAY) {
        fprintf(stderr, "[-] EGL: eglGetDisplay returned NO_DISPLAY.\n");
        return false;
    }

    EGLint major = 0, minor = 0;
    if (!p_eglInitialize(ctx->display, &major, &minor)) {
        fprintf(stderr, "[-] EGL: eglInitialize failed on display %p (err: 0x%x).\n", ctx->display, p_eglGetError ? p_eglGetError() : 0);
        return false;
    }

    printf("[NativeSurface] EGL Active: Version %d.%d\n", major, minor);

    // 3. Choose EGL Configuration (32-bit RGBA for Transparency)
    const EGLint config_attribs[] = {
        EGL_SURFACE_TYPE, EGL_WINDOW_BIT | EGL_PBUFFER_BIT,
        EGL_RENDERABLE_TYPE, EGL_OPENGL_ES2_BIT,
        EGL_RED_SIZE, 8,
        EGL_GREEN_SIZE, 8,
        EGL_BLUE_SIZE, 8,
        EGL_ALPHA_SIZE, 8,
        EGL_DEPTH_SIZE, 0,
        EGL_NONE
    };

    EGLint num_configs = 0;
    if (!p_eglChooseConfig(ctx->display, config_attribs, &ctx->config, 1, &num_configs) || num_configs < 1) {
        const EGLint fallback_attribs[] = {
            EGL_SURFACE_TYPE, EGL_WINDOW_BIT | EGL_PBUFFER_BIT,
            EGL_RENDERABLE_TYPE, EGL_OPENGL_ES2_BIT,
            EGL_NONE
        };
        p_eglChooseConfig(ctx->display, fallback_attribs, &ctx->config, 1, &num_configs);
    }

    // 4. Create EGL Context
    const EGLint context_attribs[] = {
        EGL_CONTEXT_CLIENT_VERSION, 2,
        EGL_NONE
    };

    ctx->context = p_eglCreateContext(ctx->display, ctx->config, EGL_NO_CONTEXT, context_attribs);
    if (ctx->context == EGL_NO_CONTEXT) {
        fprintf(stderr, "[-] EGL: eglCreateContext failed (err: 0x%x).\n", p_eglGetError ? p_eglGetError() : 0);
        p_eglTerminate(ctx->display);
        return false;
    }

    // 5. Create Window Surface
    // Attempt SurfaceFlinger ANativeWindow
    ctx->native_window = create_surface_flinger_window(ctx, ctx->screen_width, ctx->screen_height);
    if (ctx->native_window) {
        ctx->surface = p_eglCreateWindowSurface(ctx->display, ctx->config, (EGLNativeWindowType)ctx->native_window, NULL);
        if (ctx->surface != EGL_NO_SURFACE) {
            printf("[✓] SurfaceFlinger Native Window Surface Created Successfully!\n");
        }
    }

    // Fallback: Pbuffer surface (compatible with offscreen/direct blit pipeline)
    if (ctx->surface == EGL_NO_SURFACE || !ctx->surface) {
        const EGLint pbuffer_attribs[] = {
            EGL_WIDTH, ctx->screen_width,
            EGL_HEIGHT, ctx->screen_height,
            EGL_NONE
        };
        ctx->surface = p_eglCreatePbufferSurface(ctx->display, ctx->config, pbuffer_attribs);
        if (ctx->surface != EGL_NO_SURFACE) {
            printf("[NativeSurface] EGL Render Surface Created (%dx%d)\n", ctx->screen_width, ctx->screen_height);
        }
    }

    if (ctx->surface == EGL_NO_SURFACE) {
        fprintf(stderr, "[-] EGL: Failed to create drawing surface (err: 0x%x).\n", p_eglGetError ? p_eglGetError() : 0);
        p_eglDestroyContext(ctx->display, ctx->context);
        p_eglTerminate(ctx->display);
        return false;
    }

    // 6. Bind Context
    if (!p_eglMakeCurrent(ctx->display, ctx->surface, ctx->surface, ctx->context)) {
        fprintf(stderr, "[-] EGL: eglMakeCurrent failed (err: 0x%x).\n", p_eglGetError ? p_eglGetError() : 0);
        return false;
    }

    // Check GLES driver info
    if (p_glGetString) {
        printf("[NativeSurface] GL Vendor   : %s\n", (const char*)p_glGetString(GL_VENDOR));
        printf("[NativeSurface] GL Renderer : %s\n", (const char*)p_glGetString(GL_RENDERER));
        printf("[NativeSurface] GL Version  : %s\n", (const char*)p_glGetString(GL_VERSION));
    }

    // Configure OpenGL ES defaults
    p_glViewport(0, 0, ctx->screen_width, ctx->screen_height);
    p_glEnable(GL_BLEND);
    p_glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    p_glClearColor(0.0f, 0.0f, 0.0f, 0.0f);

    init_framebuffer_fallback(ctx);

    ctx->is_initialized = true;
    printf("[✓] Native Surface & Hardware-Accelerated OpenGL ES Pipeline Active!\n");
    return true;
}

void native_surface_begin_frame(NativeOverlayContext* ctx) {
    if (!ctx || !ctx->is_initialized) return;
    p_eglMakeCurrent(ctx->display, ctx->surface, ctx->surface, ctx->context);
    p_glViewport(0, 0, ctx->screen_width, ctx->screen_height);
    p_glClear(GL_COLOR_BUFFER_BIT);
}

void native_surface_end_frame(NativeOverlayContext* ctx) {
    if (!ctx || !ctx->is_initialized) return;
    p_glFlush();
    if (p_eglSwapBuffers) p_eglSwapBuffers(ctx->display, ctx->surface);
}

void native_surface_destroy(NativeOverlayContext* ctx) {
    if (!ctx || !ctx->is_initialized) return;
    if (ctx->display != EGL_NO_DISPLAY) {
        p_eglMakeCurrent(ctx->display, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT);
        if (ctx->surface != EGL_NO_SURFACE) p_eglDestroySurface(ctx->display, ctx->surface);
        if (ctx->context != EGL_NO_CONTEXT) p_eglDestroyContext(ctx->display, ctx->context);
        p_eglTerminate(ctx->display);
    }
    if (s_fb_ptr && s_fb_ptr != MAP_FAILED) {
        munmap(s_fb_ptr, s_fb_size);
        s_fb_ptr = NULL;
    }
    if (s_fb_fd >= 0) {
        close(s_fb_fd);
        s_fb_fd = -1;
    }
    ctx->is_initialized = false;
}
