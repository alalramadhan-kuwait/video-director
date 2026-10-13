"""Creative + voice profiles, and the cross-project contamination check."""
from __future__ import annotations
from pathlib import Path
import yaml


def load(path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding='utf-8'))


def contamination(project_profile: dict, other_profiles: list[dict], files: list) -> list[dict]:
    """Scan a project's text files (storyboards, scene code, voice configs) for another profile's signatures."""
    out = []
    for f in files:
        text = Path(f).read_text(encoding='utf-8', errors='replace')
        for other in other_profiles:
            if other['id'] == project_profile['id']:
                continue
            for sev in ('critical', 'major'):
                for sig in other.get('signatures', {}).get(sev, []):
                    if sig in text:
                        out.append({'code': 'STYLE_CONTAMINATION', 'severity': sev, 'file': str(f),
                                    'signature': sig, 'belongs_to': other['id']})
    return out


def voice_for(profile: dict, name: str, project: str) -> dict:
    """Resolve a final voice for a film, enforcing the profile's restrictions."""
    v = profile['voice']['voices'].get(name)
    if v is None:
        raise KeyError(f'{name} is not a voice of {profile["id"]}')
    if v.get('requires_authorization'):
        raise PermissionError(f'{name} needs a per-film authorization recorded by the owner')
    if v.get('approved_for') and project not in v['approved_for']:
        raise PermissionError(f'{name} is approved for {v["approved_for"]}, not {project}')
    return {'provider': v['provider'], **{k: v[k] for k in ('voice_id', 'model', 'settings', 'seed', 'output_format') if k in v}}
