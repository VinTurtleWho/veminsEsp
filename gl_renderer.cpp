#include "gl_renderer.h"
#include "gl_bindings.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <vector>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// Built-in 5x7 ASCII bitmap font (characters 32 ' ' to 126 '~')
static const uint8_t s_font5x7[95][5] = {
    {0x00,0x00,0x00,0x00,0x00}, // ' '
    {0x00,0x00,0x5F,0x00,0x00}, // '!'
    {0x00,0x07,0x00,0x07,0x00}, // '"'
    {0x14,0x7F,0x14,0x7F,0x14}, // '#'
    {0x24,0x2A,0x7F,0x2A,0x12}, // '$'
    {0x23,0x13,0x08,0x64,0x62}, // '%'
    {0x36,0x49,0x55,0x22,0x50}, // '&'
    {0x00,0x05,0x03,0x00,0x00}, // '''
    {0x00,0x1C,0x22,0x41,0x00}, // '('
    {0x00,0x41,0x22,0x1C,0x00}, // ')'
    {0x14,0x08,0x3E,0x08,0x14}, // '*'
    {0x08,0x08,0x3E,0x08,0x08}, // '+'
    {0x00,0x50,0x30,0x00,0x00}, // ','
    {0x08,0x08,0x08,0x08,0x08}, // '-'
    {0x00,0x60,0x60,0x00,0x00}, // '.'
    {0x20,0x10,0x08,0x04,0x02}, // '/'
    {0x3E,0x51,0x49,0x45,0x3E}, // '0'
    {0x00,0x42,0x7F,0x40,0x00}, // '1'
    {0x42,0x61,0x51,0x49,0x46}, // '2'
    {0x21,0x41,0x45,0x4B,0x31}, // '3'
    {0x18,0x14,0x12,0x7F,0x10}, // '4'
    {0x27,0x45,0x45,0x45,0x39}, // '5'
    {0x3C,0x4A,0x49,0x49,0x30}, // '6'
    {0x01,0x71,0x09,0x05,0x03}, // '7'
    {0x36,0x49,0x49,0x49,0x36}, // '8'
    {0x06,0x49,0x49,0x29,0x1E}, // '9'
    {0x00,0x36,0x36,0x00,0x00}, // ':'
    {0x00,0x56,0x36,0x00,0x00}, // ';'
    {0x08,0x14,0x22,0x41,0x00}, // '<'
    {0x14,0x14,0x14,0x14,0x14}, // '='
    {0x00,0x41,0x22,0x14,0x08}, // '>'
    {0x02,0x01,0x51,0x09,0x06}, // '?'
    {0x32,0x49,0x79,0x41,0x3E}, // '@'
    {0x7E,0x11,0x11,0x11,0x7E}, // 'A'
    {0x7F,0x49,0x49,0x49,0x36}, // 'B'
    {0x3E,0x41,0x41,0x41,0x22}, // 'C'
    {0x7F,0x41,0x41,0x22,0x1C}, // 'D'
    {0x7F,0x49,0x49,0x49,0x41}, // 'E'
    {0x7F,0x09,0x09,0x09,0x01}, // 'F'
    {0x3E,0x41,0x49,0x49,0x7A}, // 'G'
    {0x7F,0x08,0x08,0x08,0x7F}, // 'H'
    {0x00,0x41,0x7F,0x41,0x00}, // 'I'
    {0x20,0x40,0x41,0x3F,0x01}, // 'J'
    {0x7F,0x08,0x14,0x22,0x41}, // 'K'
    {0x7F,0x40,0x40,0x40,0x40}, // 'L'
    {0x7F,0x02,0x0C,0x02,0x7F}, // 'M'
    {0x7F,0x04,0x08,0x10,0x7F}, // 'N'
    {0x3E,0x41,0x41,0x41,0x3E}, // 'O'
    {0x7F,0x09,0x09,0x09,0x06}, // 'P'
    {0x3E,0x41,0x51,0x21,0x5E}, // 'Q'
    {0x7F,0x09,0x19,0x29,0x46}, // 'R'
    {0x46,0x49,0x49,0x49,0x31}, // 'S'
    {0x01,0x01,0x7F,0x01,0x01}, // 'T'
    {0x3F,0x40,0x40,0x40,0x3F}, // 'U'
    {0x1F,0x20,0x40,0x20,0x1F}, // 'V'
    {0x3F,0x40,0x38,0x40,0x3F}, // 'W'
    {0x63,0x14,0x08,0x14,0x63}, // 'X'
    {0x07,0x08,0x70,0x08,0x07}, // 'Y'
    {0x61,0x51,0x49,0x45,0x43}, // 'Z'
    {0x00,0x7F,0x41,0x41,0x00}, // '['
    {0x02,0x04,0x08,0x10,0x20}, // '\'
    {0x00,0x41,0x41,0x7F,0x00}, // ']'
    {0x04,0x02,0x01,0x02,0x04}, // '^'
    {0x40,0x40,0x40,0x40,0x40}, // '_'
    {0x00,0x01,0x02,0x04,0x00}, // '`'
    {0x20,0x54,0x54,0x54,0x78}, // 'a'
    {0x7F,0x48,0x44,0x44,0x38}, // 'b'
    {0x38,0x44,0x44,0x44,0x20}, // 'c'
    {0x38,0x44,0x44,0x48,0x7F}, // 'd'
    {0x38,0x54,0x54,0x54,0x18}, // 'e'
    {0x08,0x7E,0x09,0x01,0x02}, // 'f'
    {0x0C,0x52,0x52,0x52,0x3E}, // 'g'
    {0x7F,0x08,0x04,0x04,0x78}, // 'h'
    {0x00,0x44,0x7D,0x40,0x00}, // 'i'
    {0x20,0x40,0x44,0x3D,0x00}, // 'j'
    {0x7F,0x10,0x28,0x44,0x00}, // 'k'
    {0x00,0x41,0x7F,0x40,0x00}, // 'l'
    {0x7C,0x04,0x18,0x04,0x78}, // 'm'
    {0x7C,0x08,0x04,0x04,0x78}, // 'n'
    {0x38,0x44,0x44,0x44,0x38}, // 'o'
    {0x7C,0x14,0x14,0x14,0x08}, // 'p'
    {0x08,0x14,0x14,0x18,0x7C}, // 'q'
    {0x7C,0x08,0x04,0x04,0x08}, // 'r'
    {0x48,0x54,0x54,0x54,0x20}, // 's'
    {0x04,0x3F,0x44,0x40,0x20}, // 't'
    {0x3C,0x40,0x40,0x20,0x7C}, // 'u'
    {0x1C,0x20,0x40,0x20,0x1C}, // 'v'
    {0x3C,0x40,0x30,0x40,0x3C}, // 'w'
    {0x44,0x28,0x10,0x28,0x44}, // 'x'
    {0x0C,0x50,0x50,0x50,0x3C}, // 'y'
    {0x44,0x64,0x54,0x4C,0x44}  // 'z'
};

static GLuint compile_shader(GLenum type, const char* source) {
    if (!p_glCreateShader) return 0;
    GLuint shader = p_glCreateShader(type);
    p_glShaderSource(shader, 1, &source, NULL);
    p_glCompileShader(shader);
    GLint compiled = 0;
    p_glGetShaderiv(shader, GL_COMPILE_STATUS, &compiled);
    if (!compiled) {
        char info[512] = {0};
        p_glGetShaderInfoLog(shader, sizeof(info), NULL, info);
        fprintf(stderr, "[-] Shader compile error: %s\n", info);
        p_glDeleteShader(shader);
        return 0;
    }
    return shader;
}

static GLuint create_program(const char* vs_src, const char* fs_src) {
    GLuint vs = compile_shader(GL_VERTEX_SHADER, vs_src);
    GLuint fs = compile_shader(GL_FRAGMENT_SHADER, fs_src);
    if (!vs || !fs) return 0;
    GLuint prog = p_glCreateProgram();
    p_glAttachShader(prog, vs);
    p_glAttachShader(prog, fs);
    p_glLinkProgram(prog);
    GLint linked = 0;
    p_glGetProgramiv(prog, GL_LINK_STATUS, &linked);
    if (!linked) {
        char info[512] = {0};
        p_glGetProgramInfoLog(prog, sizeof(info), NULL, info);
        fprintf(stderr, "[-] Program link error: %s\n", info);
        p_glDeleteProgram(prog);
        return 0;
    }
    p_glDeleteShader(vs);
    p_glDeleteShader(fs);
    return prog;
}

GLRenderer& GLRenderer::instance() {
    static GLRenderer s_instance;
    return s_instance;
}

GLRenderer::GLRenderer() : screen_w_(2400), screen_h_(1080), is_initialized_(false) {}
GLRenderer::~GLRenderer() {}

bool GLRenderer::init(int screen_w, int screen_h) {
    screen_w_ = screen_w;
    screen_h_ = screen_h;

    // 1. Color Shader (2D Ortho)
    const char* vs_color =
        "attribute vec2 a_pos;\n"
        "uniform mat4 u_proj;\n"
        "void main() {\n"
        "    gl_Position = u_proj * vec4(a_pos, 0.0, 1.0);\n"
        "}\n";
    const char* fs_color =
        "precision mediump float;\n"
        "uniform vec4 u_color;\n"
        "void main() {\n"
        "    gl_FragColor = u_color;\n"
        "}\n";

    color_program_ = create_program(vs_color, fs_color);
    if (!color_program_) return false;
    u_color_proj_ = p_glGetUniformLocation(color_program_, "u_proj");
    u_color_val_ = p_glGetUniformLocation(color_program_, "u_color");

    // 2. Texture Shader
    const char* vs_tex =
        "attribute vec2 a_pos;\n"
        "attribute vec2 a_uv;\n"
        "uniform mat4 u_proj;\n"
        "varying vec2 v_uv;\n"
        "void main() {\n"
        "    v_uv = a_uv;\n"
        "    gl_Position = u_proj * vec4(a_pos, 0.0, 1.0);\n"
        "}\n";
    const char* fs_tex =
        "precision mediump float;\n"
        "varying vec2 v_uv;\n"
        "uniform sampler2D u_sampler;\n"
        "uniform vec4 u_tint;\n"
        "void main() {\n"
        "    vec4 c = texture2D(u_sampler, v_uv);\n"
        "    gl_FragColor = c * u_tint;\n"
        "}\n";

    texture_program_ = create_program(vs_tex, fs_tex);
    if (!texture_program_) return false;
    u_tex_proj_ = p_glGetUniformLocation(texture_program_, "u_proj");
    u_tex_sampler_ = p_glGetUniformLocation(texture_program_, "u_sampler");
    u_tex_tint_ = p_glGetUniformLocation(texture_program_, "u_tint");

    p_glGenBuffers(1, &vbo_);
    is_initialized_ = true;
    return true;
}

void GLRenderer::update_screen_size(int screen_w, int screen_h) {
    screen_w_ = screen_w;
    screen_h_ = screen_h;
}

static void make_ortho_matrix(float left, float right, float bottom, float top, float* m) {
    memset(m, 0, 16 * sizeof(float));
    m[0] = 2.0f / (right - left);
    m[5] = 2.0f / (top - bottom);
    m[10] = -1.0f;
    m[12] = -(right + left) / (right - left);
    m[13] = -(top + bottom) / (top - bottom);
    m[15] = 1.0f;
}

static void set_color_uniform(GLint location, uint32_t col) {
    float r = (float)(col & 0xFF) / 255.0f;
    float g = (float)((col >> 8) & 0xFF) / 255.0f;
    float b = (float)((col >> 16) & 0xFF) / 255.0f;
    float a = (float)((col >> 24) & 0xFF) / 255.0f;
    p_glUniform4f(location, r, g, b, a);
}

void GLRenderer::begin() {
    float proj[16];
    // Top-left origin: X from 0 to screen_w, Y from 0 to screen_h (Y points downward)
    make_ortho_matrix(0.0f, (float)screen_w_, (float)screen_h_, 0.0f, proj);

    p_glUseProgram(color_program_);
    p_glUniformMatrix4fv(u_color_proj_, 1, GL_FALSE, proj);

    p_glUseProgram(texture_program_);
    p_glUniformMatrix4fv(u_tex_proj_, 1, GL_FALSE, proj);
}

void GLRenderer::end() {}

void GLRenderer::draw_rect_filled(float x, float y, float w, float h, uint32_t color) {
    p_glUseProgram(color_program_);
    set_color_uniform(u_color_val_, color);

    float verts[] = {
        x, y,
        x + w, y,
        x, y + h,
        x + w, y + h
    };

    p_glBindBuffer(GL_ARRAY_BUFFER, vbo_);
    p_glBufferData(GL_ARRAY_BUFFER, sizeof(verts), verts, GL_STREAM_DRAW);
    GLint pos_loc = p_glGetAttribLocation(color_program_, "a_pos");
    p_glEnableVertexAttribArray(pos_loc);
    p_glVertexAttribPointer(pos_loc, 2, GL_FLOAT, GL_FALSE, 0, 0);

    p_glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);
}

void GLRenderer::draw_rect_outline(float x, float y, float w, float h, float thickness, uint32_t color) {
    draw_rect_filled(x, y, w, thickness, color); // Top
    draw_rect_filled(x, y + h - thickness, w, thickness, color); // Bottom
    draw_rect_filled(x, y, thickness, h, color); // Left
    draw_rect_filled(x + w - thickness, y, thickness, h, color); // Right
}

void GLRenderer::draw_circle_filled(float cx, float cy, float radius, uint32_t color, int segments) {
    p_glUseProgram(color_program_);
    set_color_uniform(u_color_val_, color);

    std::vector<float> verts;
    verts.push_back(cx);
    verts.push_back(cy);

    for (int i = 0; i <= segments; i++) {
        float angle = (float)i * 2.0f * (float)M_PI / (float)segments;
        verts.push_back(cx + cosf(angle) * radius);
        verts.push_back(cy + sinf(angle) * radius);
    }

    p_glBindBuffer(GL_ARRAY_BUFFER, vbo_);
    p_glBufferData(GL_ARRAY_BUFFER, verts.size() * sizeof(float), verts.data(), GL_STREAM_DRAW);
    GLint pos_loc = p_glGetAttribLocation(color_program_, "a_pos");
    p_glEnableVertexAttribArray(pos_loc);
    p_glVertexAttribPointer(pos_loc, 2, GL_FLOAT, GL_FALSE, 0, 0);

    p_glDrawArrays(GL_TRIANGLE_FAN, 0, (GLsizei)verts.size() / 2);
}

void GLRenderer::draw_circle_ring(float cx, float cy, float radius, float thickness, uint32_t color, int segments) {
    p_glUseProgram(color_program_);
    set_color_uniform(u_color_val_, color);

    float r_in = radius - thickness * 0.5f;
    float r_out = radius + thickness * 0.5f;

    std::vector<float> verts;
    for (int i = 0; i <= segments; i++) {
        float angle = (float)i * 2.0f * (float)M_PI / (float)segments;
        float c = cosf(angle);
        float s = sinf(angle);
        verts.push_back(cx + c * r_out);
        verts.push_back(cy + s * r_out);
        verts.push_back(cx + c * r_in);
        verts.push_back(cy + s * r_in);
    }

    p_glBindBuffer(GL_ARRAY_BUFFER, vbo_);
    p_glBufferData(GL_ARRAY_BUFFER, verts.size() * sizeof(float), verts.data(), GL_STREAM_DRAW);
    GLint pos_loc = p_glGetAttribLocation(color_program_, "a_pos");
    p_glEnableVertexAttribArray(pos_loc);
    p_glVertexAttribPointer(pos_loc, 2, GL_FLOAT, GL_FALSE, 0, 0);

    p_glDrawArrays(GL_TRIANGLE_STRIP, 0, (GLsizei)verts.size() / 2);
}

void GLRenderer::draw_line(float x0, float y0, float x1, float y1, float thickness, uint32_t color) {
    float dx = x1 - x0;
    float dy = y1 - y0;
    float len = sqrtf(dx * dx + dy * dy);
    if (len < 0.001f) return;

    float nx = -dy / len * (thickness * 0.5f);
    float ny = dx / len * (thickness * 0.5f);

    float verts[] = {
        x0 + nx, y0 + ny,
        x0 - nx, y0 - ny,
        x1 + nx, y1 + ny,
        x1 - nx, y1 - ny
    };

    p_glUseProgram(color_program_);
    set_color_uniform(u_color_val_, color);

    p_glBindBuffer(GL_ARRAY_BUFFER, vbo_);
    p_glBufferData(GL_ARRAY_BUFFER, sizeof(verts), verts, GL_STREAM_DRAW);
    GLint pos_loc = p_glGetAttribLocation(color_program_, "a_pos");
    p_glEnableVertexAttribArray(pos_loc);
    p_glVertexAttribPointer(pos_loc, 2, GL_FLOAT, GL_FALSE, 0, 0);

    p_glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);
}

void GLRenderer::draw_arrow(float x0, float y0, float x1, float y1, float head_size, float thickness, uint32_t color) {
    draw_line(x0, y0, x1, y1, thickness, color);

    float dx = x1 - x0;
    float dy = y1 - y0;
    float len = sqrtf(dx * dx + dy * dy);
    if (len < 0.001f) return;

    float ux = dx / len;
    float uy = dy / len;
    float nx = -uy;
    float ny = ux;

    float p0x = x1;
    float p0y = y1;
    float p1x = x1 - ux * head_size + nx * (head_size * 0.6f);
    float p1y = y1 - uy * head_size + ny * (head_size * 0.6f);
    float p2x = x1 - ux * head_size - nx * (head_size * 0.6f);
    float p2y = y1 - uy * head_size - ny * (head_size * 0.6f);

    float verts[] = { p0x, p0y, p1x, p1y, p2x, p2y };

    p_glUseProgram(color_program_);
    set_color_uniform(u_color_val_, color);

    p_glBindBuffer(GL_ARRAY_BUFFER, vbo_);
    p_glBufferData(GL_ARRAY_BUFFER, sizeof(verts), verts, GL_STREAM_DRAW);
    GLint pos_loc = p_glGetAttribLocation(color_program_, "a_pos");
    p_glEnableVertexAttribArray(pos_loc);
    p_glVertexAttribPointer(pos_loc, 2, GL_FLOAT, GL_FALSE, 0, 0);

    p_glDrawArrays(GL_TRIANGLES, 0, 3);
}

void GLRenderer::draw_textured_quad(GLuint tex_id, float x, float y, float w, float h, uint32_t tint) {
    if (!tex_id) return;

    p_glUseProgram(texture_program_);
    p_glActiveTexture(GL_TEXTURE0);
    p_glBindTexture(GL_TEXTURE_2D, tex_id);
    p_glUniform1i(u_tex_sampler_, 0);
    set_color_uniform(u_tex_tint_, tint);

    struct V { float x, y, u, v; };
    V verts[] = {
        { x,     y,     0.0f, 0.0f },
        { x + w, y,     1.0f, 0.0f },
        { x,     y + h, 0.0f, 1.0f },
        { x + w, y + h, 1.0f, 1.0f }
    };

    p_glBindBuffer(GL_ARRAY_BUFFER, vbo_);
    p_glBufferData(GL_ARRAY_BUFFER, sizeof(verts), verts, GL_STREAM_DRAW);

    GLint pos_loc = p_glGetAttribLocation(texture_program_, "a_pos");
    GLint uv_loc = p_glGetAttribLocation(texture_program_, "a_uv");

    p_glEnableVertexAttribArray(pos_loc);
    p_glVertexAttribPointer(pos_loc, 2, GL_FLOAT, GL_FALSE, sizeof(V), (void*)0);

    p_glEnableVertexAttribArray(uv_loc);
    p_glVertexAttribPointer(uv_loc, 2, GL_FLOAT, GL_FALSE, sizeof(V), (void*)(2 * sizeof(float)));

    p_glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);
    p_glBindTexture(GL_TEXTURE_2D, 0);
}

void GLRenderer::draw_textured_circle(GLuint tex_id, float cx, float cy, float radius, uint32_t border_color, float border_thickness, int segments) {
    if (tex_id > 0) {
        // Render Textured Circular Avatar
        p_glUseProgram(texture_program_);
        p_glActiveTexture(GL_TEXTURE0);
        p_glBindTexture(GL_TEXTURE_2D, tex_id);
        p_glUniform1i(u_tex_sampler_, 0);
        set_color_uniform(u_tex_tint_, 0xFFFFFFFF);

        struct V { float x, y, u, v; };
        std::vector<V> verts;
        verts.push_back({ cx, cy, 0.5f, 0.5f });

        for (int i = 0; i <= segments; i++) {
            float angle = (float)i * 2.0f * (float)M_PI / (float)segments;
            float c = cosf(angle);
            float s = sinf(angle);
            float x = cx + c * radius;
            float y = cy + s * radius;
            float u = 0.5f + c * 0.5f;
            float v = 0.5f + s * 0.5f;
            verts.push_back({ x, y, u, v });
        }

        p_glBindBuffer(GL_ARRAY_BUFFER, vbo_);
        p_glBufferData(GL_ARRAY_BUFFER, verts.size() * sizeof(V), verts.data(), GL_STREAM_DRAW);

        GLint pos_loc = p_glGetAttribLocation(texture_program_, "a_pos");
        GLint uv_loc = p_glGetAttribLocation(texture_program_, "a_uv");

        p_glEnableVertexAttribArray(pos_loc);
        p_glVertexAttribPointer(pos_loc, 2, GL_FLOAT, GL_FALSE, sizeof(V), (void*)0);

        p_glEnableVertexAttribArray(uv_loc);
        p_glVertexAttribPointer(uv_loc, 2, GL_FLOAT, GL_FALSE, sizeof(V), (void*)(2 * sizeof(float)));

        p_glDrawArrays(GL_TRIANGLE_FAN, 0, (GLsizei)verts.size());
        p_glBindTexture(GL_TEXTURE_2D, 0);
    } else {
        // Fallback filled circle
        draw_circle_filled(cx, cy, radius, border_color, segments);
    }

    // Draw Outer Border Ring
    if (border_thickness > 0.0f) {
        draw_circle_ring(cx, cy, radius + border_thickness * 0.5f, border_thickness, border_color, segments);
    }
}

void GLRenderer::draw_hp_bar(float x, float y, float w, float h, float hp_pct, float shield_pct, uint32_t hp_color) {
    if (hp_pct < 0.0f) hp_pct = 0.0f;
    if (hp_pct > 1.0f) hp_pct = 1.0f;

    // Background
    draw_rect_filled(x, y, w, h, COLOR_BG_DARK);

    // HP Fill
    float fill_w = w * hp_pct;
    if (fill_w > 0.0f) {
        draw_rect_filled(x, y, fill_w, h, hp_color);
    }

    // Shield Fill (layered over HP bar)
    if (shield_pct > 0.0f) {
        float shield_w = w * shield_pct;
        if (shield_w > w - fill_w) shield_w = w - fill_w;
        draw_rect_filled(x + fill_w, y, shield_w, h, COLOR_SHIELD_WHITE);
    }

    // Border
    draw_rect_outline(x, y, w, h, 1.0f, COLOR_RGBA(255, 255, 255, 120));
}

void GLRenderer::draw_cooldown_badge(GLuint skill_tex, float cx, float cy, float radius, float rem_s, bool is_ult) {
    uint32_t border_col = (rem_s <= 0.05f) ? COLOR_SELF_GREEN : (is_ult ? COLOR_HP_RED : COLOR_HP_YELLOW);
    draw_textured_circle(skill_tex, cx, cy, radius, border_col, 2.0f);

    if (rem_s > 0.05f) {
        // Dark translucent overlay
        draw_circle_filled(cx, cy, radius, COLOR_RGBA(0, 0, 0, 160));
        char str[16];
        if (rem_s >= 10.0f) snprintf(str, sizeof(str), "%d", (int)rem_s);
        else snprintf(str, sizeof(str), "%.1f", rem_s);

        float tw = measure_string_width(str, 1.0f);
        draw_string(cx - tw * 0.5f, cy - 3.5f, str, 1.0f, COLOR_TEXT_WHITE);
    } else if (is_ult) {
        // "RDY" badge
        draw_string(cx - 7.0f, cy - 3.5f, "RDY", 0.9f, COLOR_SELF_GREEN);
    }
}

void GLRenderer::draw_edge_chevron(float cx, float cy, float angle_deg, float size, uint32_t color) {
    float rad = angle_deg * (float)M_PI / 180.0f;
    float ux = cosf(rad);
    float uy = sinf(rad);
    float nx = -uy;
    float ny = ux;

    float p0x = cx + ux * size;
    float p0y = cy + uy * size;
    float p1x = cx - ux * (size * 0.5f) + nx * (size * 0.7f);
    float p1y = cy - uy * (size * 0.5f) + ny * (size * 0.7f);
    float p2x = cx - ux * (size * 0.5f) - nx * (size * 0.7f);
    float p2y = cy - uy * (size * 0.5f) - ny * (size * 0.7f);

    float verts[] = { p0x, p0y, p1x, p1y, p2x, p2y };

    p_glUseProgram(color_program_);
    set_color_uniform(u_color_val_, color);

    p_glBindBuffer(GL_ARRAY_BUFFER, vbo_);
    p_glBufferData(GL_ARRAY_BUFFER, sizeof(verts), verts, GL_STREAM_DRAW);
    GLint pos_loc = p_glGetAttribLocation(color_program_, "a_pos");
    p_glEnableVertexAttribArray(pos_loc);
    p_glVertexAttribPointer(pos_loc, 2, GL_FLOAT, GL_FALSE, 0, 0);

    p_glDrawArrays(GL_TRIANGLES, 0, 3);
}

float GLRenderer::measure_string_width(const char* text, float scale) {
    if (!text) return 0.0f;
    return (float)strlen(text) * 6.0f * scale;
}

void GLRenderer::draw_string(float x, float y, const char* text, float scale, uint32_t color) {
    if (!text) return;

    p_glUseProgram(color_program_);
    set_color_uniform(u_color_val_, color);

    std::vector<float> verts;
    float cur_x = x;

    for (int idx = 0; text[idx] != '\0'; idx++) {
        char c = text[idx];
        if (c < 32 || c > 126) c = '?';
        int font_idx = c - 32;

        for (int col = 0; col < 5; col++) {
            uint8_t bits = s_font5x7[font_idx][col];
            for (int row = 0; row < 7; row++) {
                if (bits & (1 << row)) {
                    float px = cur_x + (float)col * scale;
                    float py = y + (float)row * scale;
                    float s = scale;
                    // Pixel quad
                    verts.push_back(px);     verts.push_back(py);
                    verts.push_back(px + s); verts.push_back(py);
                    verts.push_back(px);     verts.push_back(py + s);
                    verts.push_back(px + s); verts.push_back(py);
                    verts.push_back(px + s); verts.push_back(py + s);
                    verts.push_back(px);     verts.push_back(py + s);
                }
            }
        }
        cur_x += 6.0f * scale;
    }

    if (verts.empty()) return;

    p_glBindBuffer(GL_ARRAY_BUFFER, vbo_);
    p_glBufferData(GL_ARRAY_BUFFER, verts.size() * sizeof(float), verts.data(), GL_STREAM_DRAW);
    GLint pos_loc = p_glGetAttribLocation(color_program_, "a_pos");
    p_glEnableVertexAttribArray(pos_loc);
    p_glVertexAttribPointer(pos_loc, 2, GL_FLOAT, GL_FALSE, 0, 0);

    p_glDrawArrays(GL_TRIANGLES, 0, (GLsizei)verts.size() / 2);
}
