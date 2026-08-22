#ifndef GL_BINDINGS_H
#define GL_BINDINGS_H

#include <EGL/egl.h>
#include <GLES2/gl2.h>
#include <dlfcn.h>
#include <stdio.h>

// EGL Function Pointers
typedef EGLDisplay (*fn_eglGetDisplay)(EGLNativeDisplayType);
typedef EGLBoolean (*fn_eglInitialize)(EGLDisplay, EGLint*, EGLint*);
typedef EGLBoolean (*fn_eglChooseConfig)(EGLDisplay, const EGLint*, EGLConfig*, EGLint, EGLint*);
typedef EGLContext (*fn_eglCreateContext)(EGLDisplay, EGLConfig, EGLContext, const EGLint*);
typedef EGLSurface (*fn_eglCreateWindowSurface)(EGLDisplay, EGLConfig, EGLNativeWindowType, const EGLint*);
typedef EGLSurface (*fn_eglCreatePbufferSurface)(EGLDisplay, EGLConfig, const EGLint*);
typedef EGLBoolean (*fn_eglMakeCurrent)(EGLDisplay, EGLSurface, EGLSurface, EGLContext);
typedef EGLBoolean (*fn_eglSwapBuffers)(EGLDisplay, EGLSurface);
typedef EGLBoolean (*fn_eglDestroySurface)(EGLDisplay, EGLSurface);
typedef EGLBoolean (*fn_eglDestroyContext)(EGLDisplay, EGLContext);
typedef EGLBoolean (*fn_eglTerminate)(EGLDisplay);
typedef void (*(*fn_eglGetProcAddress)(const char*))();
typedef EGLint (*fn_eglGetError)(void);

// GLES2 Function Pointers
typedef GLuint (*fn_glCreateShader)(GLenum);
typedef void (*fn_glShaderSource)(GLuint, GLsizei, const GLchar* const*, const GLint*);
typedef void (*fn_glCompileShader)(GLuint);
typedef void (*fn_glGetShaderiv)(GLuint, GLenum, GLint*);
typedef void (*fn_glGetShaderInfoLog)(GLuint, GLsizei, GLsizei*, GLchar*);
typedef GLuint (*fn_glCreateProgram)(void);
typedef void (*fn_glAttachShader)(GLuint, GLuint);
typedef void (*fn_glLinkProgram)(GLuint);
typedef void (*fn_glGetProgramiv)(GLuint, GLenum, GLint*);
typedef void (*fn_glGetProgramInfoLog)(GLuint, GLsizei, GLsizei*, GLchar*);
typedef void (*fn_glUseProgram)(GLuint);
typedef GLint (*fn_glGetUniformLocation)(GLuint, const GLchar*);
typedef void (*fn_glUniformMatrix4fv)(GLint, GLsizei, GLboolean, const GLfloat*);
typedef void (*fn_glUniform4f)(GLint, GLfloat, GLfloat, GLfloat, GLfloat);
typedef void (*fn_glUniform1i)(GLint, GLint);
typedef void (*fn_glGenBuffers)(GLsizei, GLuint*);
typedef void (*fn_glBindBuffer)(GLenum, GLuint);
typedef void (*fn_glBufferData)(GLenum, GLsizeiptr, const void*, GLenum);
typedef GLint (*fn_glGetAttribLocation)(GLuint, const GLchar*);
typedef void (*fn_glEnableVertexAttribArray)(GLuint);
typedef void (*fn_glVertexAttribPointer)(GLuint, GLint, GLenum, GLboolean, GLsizei, const void*);
typedef void (*fn_glDrawArrays)(GLenum, GLint, GLsizei);
typedef void (*fn_glViewport)(GLint, GLint, GLsizei, GLsizei);
typedef void (*fn_glEnable)(GLenum);
typedef void (*fn_glBlendFunc)(GLenum, GLenum);
typedef void (*fn_glClearColor)(GLclampf, GLclampf, GLclampf, GLclampf);
typedef void (*fn_glClear)(GLbitfield);
typedef void (*fn_glFlush)(void);
typedef void (*fn_glActiveTexture)(GLenum);
typedef void (*fn_glBindTexture)(GLenum, GLuint);
typedef void (*fn_glTexParameteri)(GLenum, GLenum, GLint);
typedef void (*fn_glTexImage2D)(GLenum, GLint, GLint, GLsizei, GLsizei, GLint, GLenum, GLenum, const void*);
typedef void (*fn_glGenTextures)(GLsizei, GLuint*);
typedef void (*fn_glDeleteTextures)(GLsizei, const GLuint*);
typedef void (*fn_glDeleteShader)(GLuint);
typedef void (*fn_glDeleteProgram)(GLuint);
typedef void (*fn_glDeleteBuffers)(GLsizei, const GLuint*);
typedef const GLubyte* (*fn_glGetString)(GLenum);
typedef GLenum (*fn_glGetError)(void);

// Global Declarations
extern fn_eglGetDisplay p_eglGetDisplay;
extern fn_eglInitialize p_eglInitialize;
extern fn_eglChooseConfig p_eglChooseConfig;
extern fn_eglCreateContext p_eglCreateContext;
extern fn_eglCreateWindowSurface p_eglCreateWindowSurface;
extern fn_eglCreatePbufferSurface p_eglCreatePbufferSurface;
extern fn_eglMakeCurrent p_eglMakeCurrent;
extern fn_eglSwapBuffers p_eglSwapBuffers;
extern fn_eglDestroySurface p_eglDestroySurface;
extern fn_eglDestroyContext p_eglDestroyContext;
extern fn_eglTerminate p_eglTerminate;
extern fn_eglGetProcAddress p_eglGetProcAddress;
extern fn_eglGetError p_eglGetError;

extern fn_glCreateShader p_glCreateShader;
extern fn_glShaderSource p_glShaderSource;
extern fn_glCompileShader p_glCompileShader;
extern fn_glGetShaderiv p_glGetShaderiv;
extern fn_glGetShaderInfoLog p_glGetShaderInfoLog;
extern fn_glCreateProgram p_glCreateProgram;
extern fn_glAttachShader p_glAttachShader;
extern fn_glLinkProgram p_glLinkProgram;
extern fn_glGetProgramiv p_glGetProgramiv;
extern fn_glGetProgramInfoLog p_glGetProgramInfoLog;
extern fn_glUseProgram p_glUseProgram;
extern fn_glGetUniformLocation p_glGetUniformLocation;
extern fn_glUniformMatrix4fv p_glUniformMatrix4fv;
extern fn_glUniform4f p_glUniform4f;
extern fn_glUniform1i p_glUniform1i;
extern fn_glGenBuffers p_glGenBuffers;
extern fn_glBindBuffer p_glBindBuffer;
extern fn_glBufferData p_glBufferData;
extern fn_glGetAttribLocation p_glGetAttribLocation;
extern fn_glEnableVertexAttribArray p_glEnableVertexAttribArray;
extern fn_glVertexAttribPointer p_glVertexAttribPointer;
extern fn_glDrawArrays p_glDrawArrays;
extern fn_glViewport p_glViewport;
extern fn_glEnable p_glEnable;
extern fn_glBlendFunc p_glBlendFunc;
extern fn_glClearColor p_glClearColor;
extern fn_glClear p_glClear;
extern fn_glFlush p_glFlush;
extern fn_glActiveTexture p_glActiveTexture;
extern fn_glBindTexture p_glBindTexture;
extern fn_glTexParameteri p_glTexParameteri;
extern fn_glTexImage2D p_glTexImage2D;
extern fn_glGenTextures p_glGenTextures;
extern fn_glDeleteTextures p_glDeleteTextures;
extern fn_glDeleteShader p_glDeleteShader;
extern fn_glDeleteProgram p_glDeleteProgram;
extern fn_glDeleteBuffers p_glDeleteBuffers;
extern fn_glGetString p_glGetString;
extern fn_glGetError p_glGetError;

bool init_gl_bindings();

#endif // GL_BINDINGS_H
