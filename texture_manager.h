#ifndef TEXTURE_MANAGER_H
#define TEXTURE_MANAGER_H

#include <stdint.h>
#include <stdbool.h>
#include <string>
#include <unordered_map>
#include <GLES2/gl2.h>

class TextureManager {
public:
    static TextureManager& instance();

    void init(const std::string& base_assets_dir = "");

    // Hero Avatar Texture Loader (<hero_id>.png)
    GLuint get_hero_icon(int hero_id);

    // Skill Icon Texture Loader (<spell_id>.png)
    GLuint get_skill_icon(int spell_id);

    // Battle Spell Icon Texture Loader (<spell_name_or_id>.png)
    GLuint get_spell_icon(int spell_id);

    // Direct path loader
    GLuint load_texture_from_file(const std::string& file_path);

    void clear_cache();

private:
    TextureManager();
    ~TextureManager();

    std::string assets_dir_;
    std::unordered_map<int, GLuint> hero_textures_;
    std::unordered_map<int, GLuint> skill_textures_;
    std::unordered_map<int, GLuint> spell_textures_;
    std::unordered_map<std::string, GLuint> file_textures_;
};

#endif // TEXTURE_MANAGER_H
