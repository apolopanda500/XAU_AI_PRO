import re

path = 'app/tabs/dashboard.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Corrigir o bloco _apply_services que está quebrado
old_block = """        if svc.get("mt5"):
            self._set_service("mt5", True,
                              text="AUTOTRADING OFF" if svc.get("mt5_warn") else None,
                              color=Theme.WARNING if svc.get("mt5_warn") else None)
                        else:
            self._set_service("mt5", False)
        for key in ("backend", "dashboard", "litellm"):
            self._set_service(key, bool(svc.get(key, False)))
        self._set_service("robot", bool(svc.get("robot", False)))"""

new_block = """        if svc.get("mt5"):
            self._set_service("mt5", True,
                              text="AUTOTRADING OFF" if svc.get("mt5_warn") else None,
                              color=Theme.WARNING if svc.get("mt5_warn") else None)
        else:
            self._set_service("mt5", False)
        for key in ("backend", "dashboard", "litellm"):
            self._set_service(key, bool(svc.get(key, False)))
        self._set_service("robot", bool(svc.get("robot", False)))"""

content = content.replace(old_block, new_block)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Indentacao corrigida!")