import os
import shutil

TEMPLATE_PATH = "momentum_placeholder_file.py"
OUTPUT_DIR = "sites"
MAIN_PATH = "main.py"
GUI_PATH = "gui.py"


def prompt_input(prompt, default=None):
    value = input(
        f"{prompt}{f' (default: {default})' if default else ''}: ").strip()
    return value or default


def update_main(site_name):
    with open(MAIN_PATH, "r") as f:
        lines = f.readlines()

    print(lines)
    import_line = f"from sites.{site_name} import run_{site_name}\n"
    case_line = f"    elif args.site == '{site_name}':\n        run_{site_name}()\n"

    with open(MAIN_PATH, "w") as f:
        for line in lines:
            f.write(line)
            if line.strip().startswith("# AUTOIMPORT"):
                f.write(import_line)
            if line.strip().startswith("# AUTORUN"):
                f.write(case_line)


def update_gui(site_name):
    site_display_name = site_name.capitalize()
    with open(GUI_PATH, "r") as f:
        lines = f.readlines()

    new_entry = f'    "{site_display_name}": run_{site_name},\n'
    import_line = f"from sites.{site_name} import run_{site_name}\n"

    with open(GUI_PATH, "w") as f:
        for line in lines:
            f.write(line)
            if line.strip().startswith("# AUTOIMPORT"):
                f.write(import_line)
            if line.strip().startswith("# AUTOSITES"):
                f.write(new_entry)


def create_script(site_name, base_url, api_key, device_key):
    dest_path = os.path.join(OUTPUT_DIR, f"{site_name}.py")

    with open(TEMPLATE_PATH, "r") as template:
        content = template.read()

    content = content.replace("FIRSTUPPERCASE", site_name.capitalize())
    content = content.replace("UPPERCASE", site_name.upper())
    content = content.replace("LOWERCASE", site_name.lower())
    content = content.replace("PLACEHOLDER-fastighet.momentum.se/Prod/placeholder", base_url)
    content = content.replace("APINUMBER", api_key)
    content = content.replace("DEVICENUMBER", device_key)
    content = content.replace("USERNAME", site_name.upper() + "_USERNAME")
    content = content.replace("PASSWORD", site_name.upper() + "_PASSWORD")

    with open(dest_path, "w") as f:
        f.write(content)

    print(f"✅ Skapade {dest_path}")


def main():
    print("🆕 Lägg till ny Momentum-baserad sajt")
    site_name = prompt_input("Ange kortnamn för sajten (t.ex. byggvesta)")
    base_url = prompt_input("Ange base URL (utan https:// och /PmApi...)",
                            f"{site_name}.momentum.se/Prod/{site_name.capitalize()}")
    api_key = prompt_input("Ange API-nyckel")
    device_key = prompt_input("Ange Device Key")

    create_script(site_name, base_url, api_key, device_key)
    update_main(site_name)
    update_gui(site_name)
    print("\n🚀 Klar! Lägg till dina miljövariabler i .env för användarnamn/lösenord.")


if __name__ == "__main__":
    main()
