#include "texture_manager.h"
#include "gl_bindings.h"
#include <stdio.h>
#include <unistd.h>
#include <sys/stat.h>

#define STB_IMAGE_IMPLEMENTATION
#include "stb_image.h"

TextureManager& TextureManager::instance() {
    static TextureManager s_instance;
    return s_instance;
}

TextureManager::TextureManager() {
    assets_dir_ = "/data/local/tmp/assets";
}

TextureManager::~TextureManager() {
    clear_cache();
}

void TextureManager::init(const std::string& base_assets_dir) {
    if (!base_assets_dir.empty()) {
        assets_dir_ = base_assets_dir;
    } else {
        // Search common locations in order of priority inside VM and storage
        const char* paths[] = {
            "/data/local/tmp/assets",
            "/data/local/tmp/veminsEsp/assets",
            "/sdcard/veminsEsp/assets",
            "/sdcard/Download/assets",
            "/sdcard/assets",
            "/storage/emulated/0/veminsEsp/assets",
            "/storage/emulated/0/Download/assets",
            "/data/data/com.termux/files/home/veminsEsp/assets",
            "./assets",
            "assets"
        };
        for (const char* p : paths) {
            struct stat st;
            if (stat(p, &st) == 0 && S_ISDIR(st.st_mode)) {
                assets_dir_ = p;
                break;
            }
        }
    }
    printf("[TextureManager] Using assets directory: %s\n", assets_dir_.c_str());
}

GLuint TextureManager::load_texture_from_file(const std::string& file_path) {
    auto it = file_textures_.find(file_path);
    if (it != file_textures_.end()) {
        return it->second;
    }

    int width = 0, height = 0, channels = 0;
    stbi_set_flip_vertically_on_load(0); // Top-left origin for 2D UI
    unsigned char* data = stbi_load(file_path.c_str(), &width, &height, &channels, 4);
    if (!data) {
        return 0;
    }

    GLuint tex_id = 0;
    if (p_glGenTextures) {
        p_glGenTextures(1, &tex_id);
        p_glBindTexture(GL_TEXTURE_2D, tex_id);

        p_glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
        p_glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
        p_glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
        p_glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);

        p_glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, data);
        p_glBindTexture(GL_TEXTURE_2D, 0);
    }

    stbi_image_free(data);
    file_textures_[file_path] = tex_id;
    return tex_id;
}

GLuint TextureManager::get_hero_icon(int hero_id) {
    if (hero_id <= 0) return 0;
    auto it = hero_textures_.find(hero_id);
    if (it != hero_textures_.end()) {
        return it->second;
    }

    char path[512];
    snprintf(path, sizeof(path), "%s/heroes/%d.png", assets_dir_.c_str(), hero_id);
    GLuint tex = load_texture_from_file(path);
    if (!tex) {
        // Try without extension
        snprintf(path, sizeof(path), "%s/heroes/%d", assets_dir_.c_str(), hero_id);
        tex = load_texture_from_file(path);
    }

    hero_textures_[hero_id] = tex;
    return tex;
}

GLuint TextureManager::get_skill_icon(int spell_id) {
    if (spell_id <= 0) return 0;
    auto it = skill_textures_.find(spell_id);
    if (it != skill_textures_.end()) {
        return it->second;
    }

    char path[512];
    snprintf(path, sizeof(path), "%s/skills/%d.png", assets_dir_.c_str(), spell_id);
    GLuint tex = load_texture_from_file(path);

    skill_textures_[spell_id] = tex;
    return tex;
}

GLuint TextureManager::get_spell_icon(int spell_id) {
    if (spell_id <= 0) return 0;
    auto it = spell_textures_.find(spell_id);
    if (it != spell_textures_.end()) {
        return it->second;
    }

    char path[512];
    snprintf(path, sizeof(path), "%s/spells/%d.png", assets_dir_.c_str(), spell_id);
    GLuint tex = load_texture_from_file(path);

    spell_textures_[spell_id] = tex;
    return tex;
}

void TextureManager::clear_cache() {
    for (auto& pair : file_textures_) {
        if (pair.second && p_glDeleteTextures) p_glDeleteTextures(1, &pair.second);
    }
    file_textures_.clear();
    hero_textures_.clear();
    skill_textures_.clear();
    spell_textures_.clear();
}
