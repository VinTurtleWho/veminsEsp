#!/usr/bin/env python3
"""
fetch_assets.py - VEMINS ESP Asset Fetcher & Generator

Downloads and indexes:
1. Hero Portrait Avatars -> assets/heroes/<hero_id>.png
2. Battle Spell Icons    -> assets/spells/<spell_id>.png
3. Hero Skill Icons      -> assets/skills/<skill_id>.png
4. Minimap Objective Map -> assets/objectives/<type>.png
5. Unified Manifest      -> assets/manifest.json
"""

import os
import sys
import json
import time
import urllib.request
import urllib.parse
from typing import Dict, Any, List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
HEROES_DIR = os.path.join(ASSETS_DIR, "heroes")
SPELLS_DIR = os.path.join(ASSETS_DIR, "spells")
SKILLS_DIR = os.path.join(ASSETS_DIR, "skills")
OBJECTIVES_DIR = os.path.join(ASSETS_DIR, "objectives")

WIKI_API = "https://mobile-legends.fandom.com/api.php"
USER_AGENT = "VeminsEsp/1.0 (Mozilla/5.0; Android; Termux)"


def ensure_dirs():
    for d in (ASSETS_DIR, HEROES_DIR, SPELLS_DIR, SKILLS_DIR, OBJECTIVES_DIR):
        os.makedirs(d, exist_ok=True)


def get_wiki_image_url(filename: str) -> str:
    """Resolves direct CDN URL for a file from Fandom MediaWiki API."""
    params = {
        "action": "query",
        "titles": f"File:{filename}",
        "prop": "imageinfo",
        "iiprop": "url",
        "format": "json"
    }
    url = f"{WIKI_API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            pages = data.get("query", {}).get("pages", {})
            for pid, pdata in pages.items():
                infos = pdata.get("imageinfo", [])
                if infos:
                    return infos[0].get("url", "")
    except Exception:
        pass
    return ""


def download_file(url: str, target_path: str) -> bool:
    if not url or os.path.exists(target_path):
        return True
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            content = resp.read()
            if len(content) > 100:
                with open(target_path, "wb") as f:
                    f.write(content)
                return True
    except Exception:
        pass
    return False


def fetch_all_battle_spells() -> Dict[str, str]:
    print("\n[+] Fetching Battle Spell Icons...")
    spells_file = os.path.join(BASE_DIR, "knowledge", "normalized", "battle_spells.json")
    if not os.path.exists(spells_file):
        return {}

    with open(spells_file, "r") as f:
        spells_data = json.load(f)

    manifest_spells = {}
    for spell_id, sinfo in spells_data.items():
        name = sinfo.get("name", "")
        if not name:
            continue
        filename = f"{name}.png"
        target_path = os.path.join(SPELLS_DIR, f"{spell_id}.png")
        name_path = os.path.join(SPELLS_DIR, f"{name.lower()}.png")

        if not os.path.exists(target_path):
            img_url = get_wiki_image_url(filename)
            if img_url:
                download_file(img_url, target_path)

        if os.path.exists(target_path):
            if not os.path.exists(name_path):
                try:
                    with open(target_path, "rb") as sf, open(name_path, "wb") as df:
                        df.write(sf.read())
                except Exception:
                    pass
            print(f"  [✓] Spell: {name} (ID {spell_id}) -> {target_path}")
            manifest_spells[spell_id] = target_path

    return manifest_spells


def fetch_all_heroes() -> Dict[str, str]:
    print("\n[+] Fetching Hero Portraits...")
    heroes_file = os.path.join(BASE_DIR, "knowledge", "normalized", "heroes.json")
    if not os.path.exists(heroes_file):
        return {}

    with open(heroes_file, "r") as f:
        heroes_data = json.load(f)

    manifest_heroes = {}
    total = len(heroes_data)
    count = 0

    for hero_id, hinfo in heroes_data.items():
        name = hinfo.get("name", "")
        if not name:
            continue
        count += 1

        target_path = os.path.join(HEROES_DIR, f"{hero_id}.png")
        name_path = os.path.join(HEROES_DIR, f"{name.lower().replace(' ', '_')}.png")

        if os.path.exists(target_path):
            manifest_heroes[hero_id] = target_path
            continue

        int_id = int(hero_id)
        candidates = [
            f"Hero{int_id:02d}1-icon.png",
            f"Hero{int_id}1-icon.png",
            f"Hero{int_id:03d}1-icon.png",
            f"{name}_Hero.png",
            f"{name}.png"
        ]

        img_url = ""
        for cand in candidates:
            img_url = get_wiki_image_url(cand)
            if img_url:
                break

        if img_url:
            ok = download_file(img_url, target_path)
            if ok:
                if not os.path.exists(name_path):
                    try:
                        with open(target_path, "rb") as sf, open(name_path, "wb") as df:
                            df.write(sf.read())
                    except Exception:
                        pass
                print(f"  [{count}/{total}] Hero: {name} (ID {hero_id}) -> {target_path}")
                manifest_heroes[hero_id] = target_path
        time.sleep(0.08)

    return manifest_heroes


def get_hero_skill_sections(hero_name: str) -> Dict[str, List[str]]:
    """Fetches section images for abilities (Passive, Skill 1, Skill 2, Ultimate)."""
    url = f"{WIKI_API}?action=parse&page={urllib.parse.quote(hero_name)}&prop=sections&format=json"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    skill_images = {"passive": [], "skill1": [], "skill2": [], "ult": []}
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            sections = data.get("parse", {}).get("sections", [])
            for s in sections:
                line = s.get("line", "").lower()
                sec_idx = s.get("index")
                slot = None
                if "passive" in line:
                    slot = "passive"
                elif "skill 1" in line or "first skill" in line:
                    slot = "skill1"
                elif "skill 2" in line or "second skill" in line:
                    slot = "skill2"
                elif "ultimate" in line or "skill 3" in line or "third skill" in line:
                    slot = "ult"

                if slot and sec_idx:
                    sec_url = f"{WIKI_API}?action=parse&page={urllib.parse.quote(hero_name)}&section={sec_idx}&prop=images&format=json"
                    sec_req = urllib.request.Request(sec_url, headers={"User-Agent": USER_AGENT})
                    with urllib.request.urlopen(sec_req, timeout=5) as s_resp:
                        s_data = json.loads(s_resp.read().decode())
                        imgs = s_data.get("parse", {}).get("images", [])
                        valid_imgs = [img for img in imgs if not any(x in img.lower() for x in ["tag", "model", "art", "skin", "icon", "lane", "diamond", "points"])]
                        if valid_imgs:
                            skill_images[slot] = valid_imgs
    except Exception:
        pass
    return skill_images


def fetch_all_skills() -> Dict[str, str]:
    print("\n[+] Fetching Hero Skill Icons...")
    heroes_file = os.path.join(BASE_DIR, "knowledge", "normalized", "heroes.json")
    if not os.path.exists(heroes_file):
        return {}

    with open(heroes_file, "r") as f:
        heroes_data = json.load(f)

    manifest_skills = {}
    total = len(heroes_data)
    count = 0

    for hero_id, hinfo in heroes_data.items():
        name = hinfo.get("name", "")
        if not name:
            continue
        count += 1
        int_id = int(hero_id)
        hero_skills_dir = os.path.join(SKILLS_DIR, str(int_id))
        os.makedirs(hero_skills_dir, exist_ok=True)

        slots = [
            ("passive", int_id * 100),
            ("skill1", int_id * 100 + 10),
            ("skill2", int_id * 100 + 20),
            ("ult", int_id * 100 + 30)
        ]

        # Check if all slots exist
        all_exist = True
        for slot_name, sid in slots:
            sid_path = os.path.join(SKILLS_DIR, f"{sid}.png")
            if not os.path.exists(sid_path):
                all_exist = False
                break

        if all_exist:
            for _, sid in slots:
                manifest_skills[str(sid)] = os.path.join(SKILLS_DIR, f"{sid}.png")
            continue

        skill_map = get_hero_skill_sections(name)
        for slot_name, sid in slots:
            sid_path = os.path.join(SKILLS_DIR, f"{sid}.png")
            slot_path = os.path.join(hero_skills_dir, f"{slot_name}.png")
            imgs = skill_map.get(slot_name, [])
            if imgs:
                img_name = imgs[0]
                img_url = get_wiki_image_url(img_name)
                if img_url:
                    ok = download_file(img_url, sid_path)
                    if ok:
                        try:
                            with open(sid_path, "rb") as sf, open(slot_path, "wb") as df:
                                df.write(sf.read())
                        except Exception:
                            pass
                        manifest_skills[str(sid)] = sid_path

        print(f"  [{count}/{total}] Skills for {name} (ID {hero_id}) mapped.")
        time.sleep(0.08)

    return manifest_skills


def main():
    print("=================================================================")
    print("           VEMINS ESP - ASSET FETCHER & INDEXER                  ")
    print("=================================================================")
    ensure_dirs()

    spells_manifest = fetch_all_battle_spells()
    heroes_manifest = fetch_all_heroes()
    skills_manifest = fetch_all_skills()

    manifest = {
        "version": "1.0.0",
        "heroes": heroes_manifest,
        "spells": spells_manifest,
        "skills": skills_manifest,
        "hero_count": len(heroes_manifest),
        "spell_count": len(spells_manifest),
        "skill_count": len(skills_manifest)
    }

    manifest_path = os.path.join(ASSETS_DIR, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print("\n=================================================================")
    print(f"[✓] Asset indexing complete!")
    print(f"    • Heroes Indexed: {len(heroes_manifest)}")
    print(f"    • Spells Indexed: {len(spells_manifest)}")
    print(f"    • Skills Indexed: {len(skills_manifest)}")
    print(f"    • Manifest Saved: {manifest_path}")
    print("=================================================================")


if __name__ == "__main__":
    main()
