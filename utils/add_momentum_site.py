import os
import shutil

TEMPLATE_PATH = "momentum_placeholder_file.py"
OUTPUT_DIR = "sites/momentum"
MAIN_PATH = "main.py"
GUI_PATH = "gui.py"


def prompt_input(prompt, default=None):
    value = input(
        f"{prompt}{f' (default: {default})' if default else ''}: ").strip()
    return value or default


def update_main(short_name):
    with open(MAIN_PATH, "r") as f:
        lines = f.readlines()

    print(lines)
    import_line = f"from sites.momentun.{short_name} import run_{short_name}\n"
    function_line = f"run_{short_name}()"
    case_line = f"    elif site == '{short_name}':\n        run_{short_name}()\n"

    with open(MAIN_PATH, "w") as f:
        for line in lines:
            f.write(line)
            if line.strip().startswith("# AUTOIMPORT"):
                f.write(import_line)
            if line.strip().startswith("# AUTORUN"):
                f.write(case_line)
            if line.strip().startswith("# FUNCTION"):
                f.write(function_line)


def update_gui(short_name):
    site_display_name = short_name.capitalize()
    with open(GUI_PATH, "r") as f:
        lines = f.readlines()

    new_entry = f'    "{site_display_name}": run_{short_name},\n'
    import_line = f"from sites.momentum.{short_name} import run_{short_name}\n"

    with open(GUI_PATH, "w") as f:
        for line in lines:
            f.write(line)
            if line.strip().startswith("# AUTOIMPORT"):
                f.write(import_line)
            if line.strip().startswith("# AUTOSITES"):
                f.write(new_entry)


def create_script(short_name, base_url, api_key, device_key):
    dest_path = os.path.join(OUTPUT_DIR, f"{short_name}.py")

    with open(TEMPLATE_PATH, "r") as template:
        content = template.read()

    content = content.replace("FIRSTUPPERCASE", short_name.capitalize())
    content = content.replace("UPPERCASE", short_name.upper())
    content = content.replace("LOWERCASE", short_name.lower())
    content = content.replace(
        "LOWERCASE-fastighet.momentum.se/Prod/FIRSTUPPERCASE", base_url)
    content = content.replace("APINUMBER", api_key)
    content = content.replace("DEVICENUMBER", device_key)
    content = content.replace("USERNAME", short_name.upper() + "_USERNAME")
    content = content.replace("PASSWORD", short_name.upper() + "_PASSWORD")

    with open(dest_path, "w") as f:
        f.write(content)

    print(f"✅ Skapade {dest_path}")


def main():
    print("🆕 Lägg till ny Momentum-baserad sajt")
    long_name = prompt_input("Ange det långa namnet för sajten (t.ex. Karlstads Bostads AB)")
    short_name = prompt_input("Ange kortnamn för sajten (t.ex. kbab)")
    base_url = prompt_input("Ange base URL (utan https:// och /PmApi...)",
                            f"{short_name}-fastighet.momentum.se/Prod/{short_name.capitalize()}")
    api_key = prompt_input("Ange API-nyckel")
    device_key = prompt_input("Ange Device Key")

    create_script(short_name, base_url, api_key, device_key)
    update_main(short_name)
    update_gui(short_name)
    print("\n🚀 Klar! Lägg till dina miljövariabler i .env för användarnamn/lösenord.")


if __name__ == "__main__":
    main()
