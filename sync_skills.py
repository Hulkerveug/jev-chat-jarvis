#!/usr/bin/env python3
"""Sync skills across all Hermes profiles."""
import os
import shutil
from pathlib import Path

PROFILES_DIR = Path("C:/Users/Nishan/AppData/Local/hermes/profiles")
EXCLUDED = {"xtobe-sami-mode"}  # Profile-specific skill, don't copy to others

def get_skills(profile):
    skills_dir = PROFILES_DIR / profile / "skills"
    if not skills_dir.exists():
        return set()
    return {d.name for d in skills_dir.iterdir() if d.is_dir() and not d.name.startswith(".")}

def copy_skill(src, dst, skill_name):
    """Copy a skill directory from src to dst."""
    src_dir = src / skill_name
    dst_dir = dst / skill_name
    if dst_dir.exists():
        return False  # Already exists
    shutil.copytree(src_dir, dst_dir)
    return True

# Get all skills across all profiles
all_skills = {}
for profile in sorted(os.listdir(PROFILES_DIR)):
    profile_dir = PROFILES_DIR / profile
    if profile_dir.is_dir() and (profile_dir / "skills").exists():
        skills = get_skills(profile)
        all_skills[profile] = skills
        print(f"{profile}: {len(skills)} skills")

# Union of all skills
union = set()
for skills in all_skills.values():
    union.update(skills)
print(f"\nTotal unique skills: {len(union)}")

# For each profile, find missing skills and copy from a source profile
for profile, skills in all_skills.items():
    missing = union - skills
    if not missing:
        print(f"\n{profile}: ✓ Complete")
        continue
    
    print(f"\n{profile}: {len(missing)} missing skills: {sorted(missing)}")
    
    # Find a source profile that has each missing skill
    for skill in sorted(missing):
        # Don't copy profile-specific skills
        if skill in EXCLUDED:
            continue
            
        # Find source profile
        for src_profile, src_skills in all_skills.items():
            if skill in src_skills and src_profile != profile:
                src_dir = PROFILES_DIR / src_profile / "skills"
                dst_dir = PROFILES_DIR / profile / "skills"
                if copy_skill(src_dir, dst_dir, skill):
                    print(f"  ✓ Copied {skill} from {src_profile}")
                break

print("\n=== SYNC COMPLETE ===")
