#ifndef GL_RENDERER_H
#define GL_RENDERER_H

#include <stdint.h>
#include <stdbool.h>
#include <GLES2/gl2.h>

// Color packed as 0xAABBGGRR or uint32_t RGBA
#define COLOR_RGBA(r, g, b, a) ((uint32_t)(r) | ((uint32_t)(g) << 8) | ((uint32_t)(b) << 16) | ((uint32_t)(a) << 24))
#define COLOR_RGB(r, g, b) COLOR_RGBA(r, g, b, 255)

// Standard Tactical Colors
#define COLOR_ENEMY_RED      COLOR_RGBA(239, 68, 68, 255)
#define COLOR_ENEMY_BORDER   COLOR_RGBA(185, 28, 28, 255)
#define COLOR_ALLY_BLUE      COLOR_RGBA(59, 130, 246, 255)
#define COLOR_SELF_GREEN     COLOR_RGBA(34, 197, 94, 255)
#define COLOR_HP_GREEN       COLOR_RGBA(34, 197, 94, 255)
#define COLOR_HP_YELLOW      COLOR_RGBA(234, 179, 8, 255)
#define COLOR_HP_RED         COLOR_RGBA(239, 68, 68, 255)
#define COLOR_SHIELD_WHITE   COLOR_RGBA(248, 250, 252, 230)
#define COLOR_BG_DARK        COLOR_RGBA(15, 23, 42, 200)
#define COLOR_TEXT_WHITE     COLOR_RGBA(255, 255, 255, 255)
#define COLOR_TEXT_GOLD      COLOR_RGBA(250, 204, 21, 255)
#define COLOR_TEXT_CYAN      COLOR_RGBA(56, 189, 248, 255)
#define COLOR_LORD_PURPLE    COLOR_RGBA(168, 85, 247, 255)
#define COLOR_TURTLE_GOLD    COLOR_RGBA(234, 179, 8, 255)

class GLRenderer {
public:
    static GLRenderer& instance();

    bool init(int screen_w, int screen_h);
    void update_screen_size(int screen_w, int screen_h);

    void begin();
    void end();

    // 2D Shape Primitives
    void draw_rect_filled(float x, float y, float w, float h, uint32_t color);
    void draw_rect_outline(float x, float y, float w, float h, float thickness, uint32_t color);
    void draw_circle_filled(float cx, float cy, float radius, uint32_t color, int segments = 24);
    void draw_circle_ring(float cx, float cy, float radius, float thickness, uint32_t color, int segments = 24);
    void draw_line(float x0, float y0, float x1, float y1, float thickness, uint32_t color);
    void draw_arrow(float x0, float y0, float x1, float y1, float head_size, float thickness, uint32_t color);

    // Textured Avatar Primitives (Minimap Hero Circles & Skill Badges)
    void draw_textured_quad(GLuint tex_id, float x, float y, float w, float h, uint32_t tint = 0xFFFFFFFF);
    void draw_textured_circle(GLuint tex_id, float cx, float cy, float radius, uint32_t border_color, float border_thickness = 2.0f, int segments = 28);

    // Tactical Game HUD Components
    void draw_hp_bar(float x, float y, float w, float h, float hp_pct, float shield_pct, uint32_t hp_color = COLOR_HP_GREEN);
    void draw_cooldown_badge(GLuint skill_tex, float cx, float cy, float radius, float rem_s, bool is_ult = false);
    void draw_edge_chevron(float cx, float cy, float angle_deg, float size, uint32_t color);

    // Built-in Bitmap Font Text Rendering
    void draw_string(float x, float y, const char* text, float scale = 1.0f, uint32_t color = COLOR_TEXT_WHITE);
    float measure_string_width(const char* text, float scale = 1.0f);

private:
    GLRenderer();
    ~GLRenderer();

    int screen_w_;
    int screen_h_;

    GLuint color_program_;
    GLuint texture_program_;

    GLint u_color_proj_;
    GLint u_color_val_;
    GLint u_tex_proj_;
    GLint u_tex_sampler_;
    GLint u_tex_tint_;

    GLuint vbo_;
    bool is_initialized_;
};

#endif // GL_RENDERER_H
