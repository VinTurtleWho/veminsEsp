#include <jni.h>
#include <android/native_window_jni.h>
#include <android/log.h>
#include <pthread.h>
#include "engine_schema.h"
#include "memory_reader.h"

#define LOG_TAG "VeminsNativeJNI"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)

static pthread_mutex_t g_engine_mutex = PTHREAD_MUTEX_INITIALIZER;
static ANativeWindow *g_native_window = NULL;
static int g_surface_width = 0;
static int g_surface_height = 0;

// Overlay configuration state
static float g_minimap_x = 0.0f;
static float g_minimap_y = 0.0f;
static float g_minimap_w = 320.0f;
static float g_minimap_h = 320.0f;
static float g_scale_x = 38.0f;
static float g_scale_y = 27.0f;
static float g_rotation_deg = 0.0f;
static bool g_show_enemies = true;
static bool g_show_monsters = true;

extern "C" {

// ============================================================================
// Engine Lifecycle Management
// ============================================================================

JNIEXPORT jboolean JNICALL
Java_com_vemins_esp_engine_VeminsNativeEngine_nativeInit(JNIEnv *env, jobject thiz) {
    (void)env;
    (void)thiz;
    pthread_mutex_lock(&g_engine_mutex);
    LOGI("[VeminsNativeEngine] nativeInit called");
    memory_reader_init();
    pthread_mutex_unlock(&g_engine_mutex);
    return JNI_TRUE;
}

JNIEXPORT void JNICALL
Java_com_vemins_esp_engine_VeminsNativeEngine_nativeRelease(JNIEnv *env, jobject thiz) {
    (void)env;
    (void)thiz;
    pthread_mutex_lock(&g_engine_mutex);
    LOGI("[VeminsNativeEngine] nativeRelease called");
    memory_reader_release();
    if (g_native_window) {
        ANativeWindow_release(g_native_window);
        g_native_window = NULL;
    }
    pthread_mutex_unlock(&g_engine_mutex);
}

// ============================================================================
// File Descriptor & Companion Connection
// ============================================================================

JNIEXPORT jboolean JNICALL
Java_com_vemins_esp_engine_VeminsNativeEngine_nativeSetMemFd(
    JNIEnv *env, jobject thiz, jint fd, jint pid) {
    (void)env;
    (void)thiz;
    pthread_mutex_lock(&g_engine_mutex);
    LOGI("[VeminsNativeEngine] nativeSetMemFd: fd=%d, pid=%d", fd, pid);
    bool ok = memory_reader_set_fd(fd, pid);
    pthread_mutex_unlock(&g_engine_mutex);
    return ok ? JNI_TRUE : JNI_FALSE;
}

// ============================================================================
// Zero-Copy Binary Snapshot Polling (DirectByteBuffer)
// ============================================================================

JNIEXPORT jint JNICALL
Java_com_vemins_esp_engine_VeminsNativeEngine_nativePollSnapshot(
    JNIEnv *env, jobject thiz, jobject byte_buffer) {
    (void)thiz;
    if (!byte_buffer) return -1;

    void *buf_ptr = env->GetDirectBufferAddress(byte_buffer);
    jlong capacity = env->GetDirectBufferCapacity(byte_buffer);

    if (!buf_ptr || capacity < (jlong)sizeof(FrameSnapshotBinary)) {
        LOGE("[VeminsNativeEngine] Invalid DirectByteBuffer or capacity too small (%lld < %zu)",
             (long long)capacity, sizeof(FrameSnapshotBinary));
        return -1;
    }

    pthread_mutex_lock(&g_engine_mutex);
    FrameSnapshotBinary *snapshot = (FrameSnapshotBinary*)buf_ptr;
    int res = memory_reader_poll_frame(snapshot);
    pthread_mutex_unlock(&g_engine_mutex);
    return res;
}

// ============================================================================
// Telemetry Diagnostics
// ============================================================================

JNIEXPORT void JNICALL
Java_com_vemins_esp_engine_VeminsNativeEngine_nativeGetTelemetry(
    JNIEnv *env, jobject thiz, jfloatArray out_stats) {
    (void)thiz;
    if (!out_stats) return;
    jsize len = env->GetArrayLength(out_stats);
    if (len < 5) return;

    float fps = 0.0f, latency = 0.0f;
    memory_reader_get_stats(&fps, &latency, NULL, NULL, NULL);

    jfloat stats[5] = { fps, latency, 0.0f, 0.0f, 0.0f };
    env->SetFloatArrayRegion(out_stats, 0, 5, stats);
}

// ============================================================================
// SurfaceView / Hardware Overlay Lifecycle
// ============================================================================

JNIEXPORT jboolean JNICALL
Java_com_vemins_esp_engine_VeminsNativeEngine_nativeSurfaceCreated(
    JNIEnv *env, jobject thiz, jobject surface, jint width, jint height) {
    (void)thiz;
    pthread_mutex_lock(&g_engine_mutex);
    LOGI("[VeminsNativeEngine] nativeSurfaceCreated: %dx%d", width, height);

    if (g_native_window) {
        ANativeWindow_release(g_native_window);
        g_native_window = NULL;
    }

    if (surface) {
        g_native_window = ANativeWindow_fromSurface(env, surface);
        g_surface_width = width;
        g_surface_height = height;
        bool valid = (g_native_window != NULL);
        pthread_mutex_unlock(&g_engine_mutex);
        return valid ? JNI_TRUE : JNI_FALSE;
    }
    pthread_mutex_unlock(&g_engine_mutex);
    return JNI_FALSE;
}

JNIEXPORT void JNICALL
Java_com_vemins_esp_engine_VeminsNativeEngine_nativeSurfaceChanged(
    JNIEnv *env, jobject thiz, jobject surface, jint width, jint height) {
    (void)env;
    (void)thiz;
    (void)surface;
    pthread_mutex_lock(&g_engine_mutex);
    LOGI("[VeminsNativeEngine] nativeSurfaceChanged: %dx%d", width, height);
    g_surface_width = width;
    g_surface_height = height;
    pthread_mutex_unlock(&g_engine_mutex);
}

JNIEXPORT void JNICALL
Java_com_vemins_esp_engine_VeminsNativeEngine_nativeSurfaceDestroyed(
    JNIEnv *env, jobject thiz) {
    (void)env;
    (void)thiz;
    pthread_mutex_lock(&g_engine_mutex);
    LOGI("[VeminsNativeEngine] nativeSurfaceDestroyed");
    if (g_native_window) {
        ANativeWindow_release(g_native_window);
        g_native_window = NULL;
    }
    pthread_mutex_unlock(&g_engine_mutex);
}

// ============================================================================
// Touch Event & Configuration Dispatch
// ============================================================================

JNIEXPORT void JNICALL
Java_com_vemins_esp_engine_VeminsNativeEngine_nativeDispatchTouch(
    JNIEnv *env, jobject thiz, jint action, jfloat x, jfloat y) {
    (void)env;
    (void)thiz;
    (void)action;
    (void)x;
    (void)y;
    // Action: 0=DOWN, 1=UP, 2=MOVE
}

JNIEXPORT void JNICALL
Java_com_vemins_esp_engine_VeminsNativeEngine_nativeUpdateConfig(
    JNIEnv *env, jobject thiz,
    jfloat minimap_x, jfloat minimap_y, jfloat minimap_w, jfloat minimap_h,
    jfloat scale_x, jfloat scale_y, jfloat rotation_deg,
    jboolean show_enemies, jboolean show_monsters) {
    (void)env;
    (void)thiz;
    pthread_mutex_lock(&g_engine_mutex);
    g_minimap_x = minimap_x;
    g_minimap_y = minimap_y;
    g_minimap_w = minimap_w;
    g_minimap_h = minimap_h;
    g_scale_x = scale_x;
    g_scale_y = scale_y;
    g_rotation_deg = rotation_deg;
    g_show_enemies = (show_enemies == JNI_TRUE);
    g_show_monsters = (show_monsters == JNI_TRUE);
    pthread_mutex_unlock(&g_engine_mutex);
}

} // extern "C"
