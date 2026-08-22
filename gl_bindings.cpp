#include "gl_bindings.h"
#include <stdio.h>
#include <stdlib.h>
#include <dlfcn.h>

fn_eglGetDisplay p_eglGetDisplay = NULL;
fn_eglInitialize p_eglInitialize = NULL;
fn_eglChooseConfig p_eglChooseConfig = NULL;
fn_eglCreateContext p_eglCreateContext = NULL;
fn_eglCreateWindowSurface p_eglCreateWindowSurface = NULL;
fn_eglCreatePbufferSurface p_eglCreatePbufferSurface = NULL;
fn_eglMakeCurrent p_eglMakeCurrent = NULL;
fn_eglSwapBuffers p_eglSwapBuffers = NULL;
fn_eglDestroySurface p_eglDestroySurface = NULL;
fn_eglDestroyContext p_eglDestroyContext = NULL;
fn_eglTerminate p_eglTerminate = NULL;
fn_eglGetProcAddress p_eglGetProcAddress = NULL;
fn_eglGetError p_eglGetError = NULL;

fn_glCreateShader p_glCreateShader = NULL;
fn_glShaderSource p_glShaderSource = NULL;
fn_glCompileShader p_glCompileShader = NULL;
fn_glGetShaderiv p_glGetShaderiv = NULL;
fn_glGetShaderInfoLog p_glGetShaderInfoLog = NULL;
fn_glCreateProgram p_glCreateProgram = NULL;
fn_glAttachShader p_glAttachShader = NULL;
fn_glLinkProgram p_glLinkProgram = NULL;
fn_glGetProgramiv p_glGetProgramiv = NULL;
fn_glGetProgramInfoLog p_glGetProgramInfoLog = NULL;
fn_glUseProgram p_glUseProgram = NULL;
fn_glGetUniformLocation p_glGetUniformLocation = NULL;
fn_glUniformMatrix4fv p_glUniformMatrix4fv = NULL;
fn_glUniform4f p_glUniform4f = NULL;
fn_glUniform1i p_glUniform1i = NULL;
fn_glGenBuffers p_glGenBuffers = NULL;
fn_glBindBuffer p_glBindBuffer = NULL;
fn_glBufferData p_glBufferData = NULL;
fn_glGetAttribLocation p_glGetAttribLocation = NULL;
fn_glEnableVertexAttribArray p_glEnableVertexAttribArray = NULL;
fn_glVertexAttribPointer p_glVertexAttribPointer = NULL;
fn_glDrawArrays p_glDrawArrays = NULL;
fn_glViewport p_glViewport = NULL;
fn_glEnable p_glEnable = NULL;
fn_glBlendFunc p_glBlendFunc = NULL;
fn_glClearColor p_glClearColor = NULL;
fn_glClear p_glClear = NULL;
fn_glFlush p_glFlush = NULL;
fn_glActiveTexture p_glActiveTexture = NULL;
fn_glBindTexture p_glBindTexture = NULL;
fn_glTexParameteri p_glTexParameteri = NULL;
fn_glTexImage2D p_glTexImage2D = NULL;
fn_glGenTextures p_glGenTextures = NULL;
fn_glDeleteTextures p_glDeleteTextures = NULL;
fn_glDeleteShader p_glDeleteShader = NULL;
fn_glDeleteProgram p_glDeleteProgram = NULL;
fn_glDeleteBuffers p_glDeleteBuffers = NULL;
fn_glGetString p_glGetString = NULL;
fn_glGetError p_glGetError = NULL;

static void* s_egl_handle = NULL;
static void* s_gles_handle = NULL;

static void* resolve_gl_sym(const char* name) {
    void* sym = NULL;
    if (p_eglGetProcAddress) {
        sym = (void*)p_eglGetProcAddress(name);
    }
    if (!sym && s_gles_handle) {
        sym = dlsym(s_gles_handle, name);
    }
    if (!sym && s_egl_handle) {
        sym = dlsym(s_egl_handle, name);
    }
    if (!sym) {
        sym = dlsym(RTLD_DEFAULT, name);
    }
    return sym;
}

bool init_gl_bindings() {
    if (p_glCreateShader && p_eglGetDisplay) return true;

    const char* egl_libs[] = {
        "/system/lib64/libEGL.so",
        "/system/lib/libEGL.so",
        "/system/vendor/lib64/egl/libEGL.so",
        "libEGL.so.1",
        "libEGL.so"
    };

    for (const char* lib : egl_libs) {
        s_egl_handle = dlopen(lib, RTLD_NOW | RTLD_GLOBAL);
        if (s_egl_handle) {
            printf("[GLBindings] Loaded EGL library: %s\n", lib);
            break;
        }
    }
    if (!s_egl_handle) s_egl_handle = RTLD_DEFAULT;

    const char* gles_libs[] = {
        "/system/lib64/libGLESv2.so",
        "/system/lib/libGLESv2.so",
        "/system/vendor/lib64/egl/libGLESv2.so",
        "libGLESv2.so.2",
        "libGLESv2.so"
    };

    for (const char* lib : gles_libs) {
        s_gles_handle = dlopen(lib, RTLD_NOW | RTLD_GLOBAL);
        if (s_gles_handle) {
            printf("[GLBindings] Loaded GLES2 library: %s\n", lib);
            break;
        }
    }
    if (!s_gles_handle) s_gles_handle = RTLD_DEFAULT;

    // Load EGL
    p_eglGetDisplay = (fn_eglGetDisplay)dlsym(s_egl_handle, "eglGetDisplay");
    p_eglInitialize = (fn_eglInitialize)dlsym(s_egl_handle, "eglInitialize");
    p_eglChooseConfig = (fn_eglChooseConfig)dlsym(s_egl_handle, "eglChooseConfig");
    p_eglCreateContext = (fn_eglCreateContext)dlsym(s_egl_handle, "eglCreateContext");
    p_eglCreateWindowSurface = (fn_eglCreateWindowSurface)dlsym(s_egl_handle, "eglCreateWindowSurface");
    p_eglCreatePbufferSurface = (fn_eglCreatePbufferSurface)dlsym(s_egl_handle, "eglCreatePbufferSurface");
    p_eglMakeCurrent = (fn_eglMakeCurrent)dlsym(s_egl_handle, "eglMakeCurrent");
    p_eglSwapBuffers = (fn_eglSwapBuffers)dlsym(s_egl_handle, "eglSwapBuffers");
    p_eglDestroySurface = (fn_eglDestroySurface)dlsym(s_egl_handle, "eglDestroySurface");
    p_eglDestroyContext = (fn_eglDestroyContext)dlsym(s_egl_handle, "eglDestroyContext");
    p_eglTerminate = (fn_eglTerminate)dlsym(s_egl_handle, "eglTerminate");
    p_eglGetProcAddress = (fn_eglGetProcAddress)dlsym(s_egl_handle, "eglGetProcAddress");
    p_eglGetError = (fn_eglGetError)dlsym(s_egl_handle, "eglGetError");

    // Load GLES2
    p_glCreateShader = (fn_glCreateShader)resolve_gl_sym("glCreateShader");
    p_glShaderSource = (fn_glShaderSource)resolve_gl_sym("glShaderSource");
    p_glCompileShader = (fn_glCompileShader)resolve_gl_sym("glCompileShader");
    p_glGetShaderiv = (fn_glGetShaderiv)resolve_gl_sym("glGetShaderiv");
    p_glGetShaderInfoLog = (fn_glGetShaderInfoLog)resolve_gl_sym("glGetShaderInfoLog");
    p_glCreateProgram = (fn_glCreateProgram)resolve_gl_sym("glCreateProgram");
    p_glAttachShader = (fn_glAttachShader)resolve_gl_sym("glAttachShader");
    p_glLinkProgram = (fn_glLinkProgram)resolve_gl_sym("glLinkProgram");
    p_glGetProgramiv = (fn_glGetProgramiv)resolve_gl_sym("glGetProgramiv");
    p_glGetProgramInfoLog = (fn_glGetProgramInfoLog)resolve_gl_sym("glGetProgramInfoLog");
    p_glUseProgram = (fn_glUseProgram)resolve_gl_sym("glUseProgram");
    p_glGetUniformLocation = (fn_glGetUniformLocation)resolve_gl_sym("glGetUniformLocation");
    p_glUniformMatrix4fv = (fn_glUniformMatrix4fv)resolve_gl_sym("glUniformMatrix4fv");
    p_glUniform4f = (fn_glUniform4f)resolve_gl_sym("glUniform4f");
    p_glUniform1i = (fn_glUniform1i)resolve_gl_sym("glUniform1i");
    p_glGenBuffers = (fn_glGenBuffers)resolve_gl_sym("glGenBuffers");
    p_glBindBuffer = (fn_glBindBuffer)resolve_gl_sym("glBindBuffer");
    p_glBufferData = (fn_glBufferData)resolve_gl_sym("glBufferData");
    p_glGetAttribLocation = (fn_glGetAttribLocation)resolve_gl_sym("glGetAttribLocation");
    p_glEnableVertexAttribArray = (fn_glEnableVertexAttribArray)resolve_gl_sym("glEnableVertexAttribArray");
    p_glVertexAttribPointer = (fn_glVertexAttribPointer)resolve_gl_sym("glVertexAttribPointer");
    p_glDrawArrays = (fn_glDrawArrays)resolve_gl_sym("glDrawArrays");
    p_glViewport = (fn_glViewport)resolve_gl_sym("glViewport");
    p_glEnable = (fn_glEnable)resolve_gl_sym("glEnable");
    p_glBlendFunc = (fn_glBlendFunc)resolve_gl_sym("glBlendFunc");
    p_glClearColor = (fn_glClearColor)resolve_gl_sym("glClearColor");
    p_glClear = (fn_glClear)resolve_gl_sym("glClear");
    p_glFlush = (fn_glFlush)resolve_gl_sym("glFlush");
    p_glActiveTexture = (fn_glActiveTexture)resolve_gl_sym("glActiveTexture");
    p_glBindTexture = (fn_glBindTexture)resolve_gl_sym("glBindTexture");
    p_glTexParameteri = (fn_glTexParameteri)resolve_gl_sym("glTexParameteri");
    p_glTexImage2D = (fn_glTexImage2D)resolve_gl_sym("glTexImage2D");
    p_glGenTextures = (fn_glGenTextures)resolve_gl_sym("glGenTextures");
    p_glDeleteTextures = (fn_glDeleteTextures)resolve_gl_sym("glDeleteTextures");
    p_glDeleteShader = (fn_glDeleteShader)resolve_gl_sym("glDeleteShader");
    p_glDeleteProgram = (fn_glDeleteProgram)resolve_gl_sym("glDeleteProgram");
    p_glDeleteBuffers = (fn_glDeleteBuffers)resolve_gl_sym("glDeleteBuffers");
    p_glGetString = (fn_glGetString)resolve_gl_sym("glGetString");
    p_glGetError = (fn_glGetError)resolve_gl_sym("glGetError");

    bool ok = (p_eglGetDisplay && p_eglInitialize && p_eglMakeCurrent && p_glCreateShader && p_glDrawArrays);
    if (!ok) {
        fprintf(stderr, "[-] GLBindings: Failed to resolve core EGL/GLES symbols.\n");
    } else {
        printf("[✓] GLBindings: Successfully loaded dynamic EGL & GLES2 drivers.\n");
    }
    return ok;
}
