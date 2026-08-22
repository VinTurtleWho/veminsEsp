#ifndef NATIVE_SURFACE_H
#define NATIVE_SURFACE_H

#include <stdint.h>
#include <stdbool.h>
#include <EGL/egl.h>
#include <GLES2/gl2.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    int screen_width;
    int screen_height;
    float density;
    int orientation;
    bool is_initialized;

    // EGL State
    EGLDisplay display;
    EGLConfig config;
    EGLContext context;
    EGLSurface surface;

    // Native window handle
    void* native_window;
    void* surface_control;
    void* composer_client;
} NativeOverlayContext;

/**
 * Initializes Android Native Surface (SurfaceFlinger Top Layer) with EGL & GLES2.
 * Z-order is set to 0x7FFFFFFF (maximum overlay priority) with touch passthrough.
 */
bool native_surface_init(NativeOverlayContext* ctx, int target_w, int target_h);

/**
 * Prepares the frame for drawing (binds context, clears with transparent color 0x00000000).
 */
void native_surface_begin_frame(NativeOverlayContext* ctx);

/**
 * Swaps EGL buffers to present the drawn frame to the screen.
 */
void native_surface_end_frame(NativeOverlayContext* ctx);

/**
 * Destroys EGL context and closes native SurfaceFlinger layer.
 */
void native_surface_destroy(NativeOverlayContext* ctx);

/**
 * Dynamically queries display width and height from the system.
 */
bool native_surface_get_display_metrics(int* out_width, int* out_height);

#ifdef __cplusplus
}
#endif

#endif // NATIVE_SURFACE_H
