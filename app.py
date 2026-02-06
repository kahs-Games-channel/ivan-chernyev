import ctypes
import os
import subprocess
import sys
import threading
import time

import customtkinter as ctk
import pystray
from PIL import Image
from pystray import MenuItem as item

APP_TITLE = "Global-Zapret Control Panel v5.1.5"
APP_NAME = "GLOBAL-ZAPRET-Pro-v5.1.5"

process = None
icon = None
is_running = False
current_mode = "Оптимизированный"
current_provider = "Авто"

REQUIRED_LIST_FILES = [
    "ipset-all.txt",
    "ipset-exclude.txt",
    "list-exclude.txt",
    "list-games.txt",
    "list-general.txt",
    "list-google.txt",
    "list-ip.txt",
    "list-meta.txt",
    "list-mylist.txt",
    "list-telegram.txt",
    "list-tiktok.txt",
    "list-x.txt",
]


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def get_base() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def kill_old_instances() -> None:
    try:
        subprocess.run(
            "taskkill /F /IM winws_zapret.exe /T",
            shell=True,
            capture_output=True,
            check=False,
        )
        time.sleep(0.5)
    except Exception:
        pass


def notify(msg: str) -> None:
    global icon
    if icon:
        try:
            icon.notify(msg, "Global-Zapret")
        except Exception:
            pass


def run_service_command(command: str) -> str:
    base = get_base()
    service_path = os.path.join(base, "service.bat")

    if not os.path.exists(service_path):
        return "Файл service.bat не найден!"

    try:
        result = subprocess.run(
            [service_path, command],
            capture_output=True,
            text=True,
            encoding="cp866",
            shell=True,
            check=False,
        )
        return result.stdout + result.stderr
    except Exception as exc:
        return f"Ошибка выполнения команды: {exc}"


def get_service_status() -> str:
    try:
        result = subprocess.run(
            "sc query zapret",
            capture_output=True,
            text=True,
            encoding="cp866",
            shell=True,
            check=False,
        )
        output = result.stdout.upper()
        if "RUNNING" in output:
            return "Служба запущена"
        if "STOPPED" in output:
            return "Служба остановлена"
        return "Служба не установлена"
    except Exception:
        return "Ошибка проверки статуса"


def check_process_status() -> str:
    try:
        result = subprocess.run(
            "tasklist | findstr winws_zapret.exe",
            capture_output=True,
            text=True,
            shell=True,
            check=False,
        )
        if "winws_zapret.exe" in result.stdout:
            return "Процесс запущен"
        return "Процесс не запущен"
    except Exception:
        return "Ошибка проверки"


def check_list_files() -> list[str]:
    base = get_base()
    lists_path = os.path.join(base, "lists")
    missing_files = [
        filename
        for filename in REQUIRED_LIST_FILES
        if not os.path.exists(os.path.join(lists_path, filename))
    ]
    return missing_files


def get_provider_settings(provider: str) -> dict:
    settings = {
        "Авто": {
            "desync_methods": ["fake", "split2"],
            "repeats": 2,
            "use_fooling": True,
            "use_ip_id": False,
            "extra_rules": False,
            "google_methods": ["fake", "fakedsplit"],
            "google_repeats": 3,
            "general_methods": ["fake"],
            "general_repeats": 1,
            "games_methods": ["split2"],
            "games_repeats": 2,
        },
        "Ростелеком": {
            "desync_methods": ["fake", "split2"],
            "repeats": 3,
            "use_fooling": True,
            "use_ip_id": False,
            "extra_rules": True,
            "google_methods": ["fake", "fakedsplit", "split2"],
            "google_repeats": 4,
            "general_methods": ["fake"],
            "general_repeats": 1,
            "games_methods": ["split2", "fakedsplit"],
            "games_repeats": 3,
        },
        "МТС": {
            "desync_methods": ["fake"],
            "repeats": 2,
            "use_fooling": False,
            "use_ip_id": False,
            "extra_rules": False,
            "google_methods": ["fake", "fakedsplit"],
            "google_repeats": 3,
            "general_methods": ["fake"],
            "general_repeats": 1,
            "games_methods": ["fake"],
            "games_repeats": 2,
        },
        "Билайн": {
            "desync_methods": ["split2"],
            "repeats": 2,
            "use_fooling": True,
            "use_ip_id": True,
            "extra_rules": True,
            "google_methods": ["split2", "fakedsplit"],
            "google_repeats": 3,
            "general_methods": ["split2"],
            "general_repeats": 1,
            "games_methods": ["split2", "multisplit"],
            "games_repeats": 3,
        },
        "МегаФон": {
            "desync_methods": ["fake", "split2"],
            "repeats": 2,
            "use_fooling": True,
            "use_ip_id": False,
            "extra_rules": True,
            "google_methods": ["fake", "split2", "fakedsplit"],
            "google_repeats": 3,
            "general_methods": ["fake"],
            "general_repeats": 1,
            "games_methods": ["split2"],
            "games_repeats": 2,
        },
        "Дом.ру": {
            "desync_methods": ["fake"],
            "repeats": 2,
            "use_fooling": True,
            "use_ip_id": False,
            "extra_rules": False,
            "google_methods": ["fake", "fakedsplit"],
            "google_repeats": 3,
            "general_methods": ["fake"],
            "general_repeats": 1,
            "games_methods": ["fake"],
            "games_repeats": 2,
        },
        "TTK": {
            "desync_methods": ["fake"],
            "repeats": 2,
            "use_fooling": True,
            "use_ip_id": False,
            "extra_rules": True,
            "google_methods": ["fake", "fakedsplit"],
            "google_repeats": 3,
            "general_methods": ["fake"],
            "general_repeats": 1,
            "games_methods": ["fake", "split2"],
            "games_repeats": 2,
        },
    }
    return settings.get(provider, settings["Авто"])


def build_desync_param(methods: list[str], repeats: int) -> tuple[str, str]:
    methods = methods or ["fake"]
    return f"--dpi-desync={','.join(methods)}", f"--dpi-desync-repeats={repeats}"


def start_zapret() -> None:
    global process, is_running, current_mode, current_provider

    missing_files = check_list_files()
    if missing_files:
        error_msg = f"Отсутствуют файлы списков: {', '.join(missing_files)}"
        print(error_msg)
        notify(f"Ошибка: {error_msg}")
        return

    kill_old_instances()

    base = get_base()
    bin_path = os.path.join(base, "bin")
    lists_path = os.path.join(base, "lists")
    exe_path = os.path.join(bin_path, "winws_zapret.exe")

    if not os.path.exists(bin_path) or not os.path.exists(lists_path):
        notify("Папки bin/lists не найдены")
        return

    def lp(name: str) -> str:
        return os.path.join(lists_path, name)

    def bp(name: str) -> str:
        return os.path.join(bin_path, name)

    quic_bin = bp("quic_initial_www_google_com.bin")
    tls_bin = bp("tls_clienthello_www_google_com.bin")
    provider_settings = get_provider_settings(current_provider)

    if current_mode == "Оптимизированный":
        base_repeats = provider_settings["repeats"]
        base_methods = provider_settings["general_methods"]
        google_repeats = provider_settings["google_repeats"]
        google_methods = provider_settings["google_methods"]
        games_repeats = provider_settings["games_repeats"]
        games_methods = provider_settings["games_methods"]
    elif current_mode == "Стандарт":
        base_repeats = provider_settings["repeats"] + 1
        base_methods = provider_settings["desync_methods"]
        google_repeats = provider_settings["google_repeats"] + 1
        google_methods = provider_settings["google_methods"]
        games_repeats = provider_settings["games_repeats"] + 1
        games_methods = provider_settings["games_methods"]
    elif current_mode == "Агрессив":
        base_repeats = provider_settings["repeats"] + 2
        base_methods = provider_settings["desync_methods"]
        google_repeats = provider_settings["google_repeats"] + 2
        google_methods = provider_settings["google_methods"]
        games_repeats = provider_settings["games_repeats"] + 2
        games_methods = provider_settings["games_methods"]
        if "multisplit" not in google_methods:
            google_methods.append("multisplit")
    else:
        base_repeats = provider_settings["repeats"] + 1
        base_methods = provider_settings["general_methods"]
        google_repeats = provider_settings["google_repeats"] + 3
        google_methods = ["fake", "fakedsplit", "split2", "multisplit"]
        games_repeats = provider_settings["games_repeats"] + 3
        games_methods = ["split2", "multisplit", "fakedsplit"]

    _, _ = build_desync_param(base_methods, base_repeats)
    google_desync, google_repeats_param = build_desync_param(google_methods, google_repeats)
    games_desync, games_repeats_param = build_desync_param(games_methods, games_repeats)

    cmd = [exe_path]
    cmd.extend([
        "--wf-tcp=80,443,2053,2083,2087,2096,8443",
        "--wf-udp=443,19294-19344,50000-50100",
    ])
    cmd.extend([
        "--filter-udp=443",
        f"--hostlist={lp('list-general.txt')}",
        f"--hostlist-exclude={lp('list-exclude.txt')}",
        f"--ipset-exclude={lp('ipset-exclude.txt')}",
        "--dpi-desync=fake",
        f"--dpi-desync-repeats={base_repeats}",
        f"--dpi-desync-fake-quic={quic_bin}",
        "--new",
        "--filter-udp=19294-19344,50000-50100",
        "--filter-l7=discord,stun",
        "--dpi-desync=fake",
        f"--dpi-desync-repeats={base_repeats}",
        "--new",
    ])

    cmd.extend([
        "--filter-tcp=2053,2083,2087,2096,8443",
        "--hostlist-domains=discord.media",
        "--dpi-desync=fake,fakedsplit",
        f"--dpi-desync-repeats={base_repeats + 1}",
        "--dpi-desync-fooling=ts" if provider_settings["use_fooling"] else "",
        "--dpi-desync-fakedsplit-pattern=0x00",
        f"--dpi-desync-fake-tls={tls_bin}",
        "--new",
    ])

    google_params = []
    if provider_settings["use_ip_id"]:
        google_params.append("--ip-id=zero")
    google_params.extend([google_desync, google_repeats_param])
    if provider_settings["use_fooling"]:
        google_params.append("--dpi-desync-fooling=ts")
    google_params.extend([
        "--dpi-desync-fakedsplit-pattern=0x00",
        f"--dpi-desync-fake-tls={tls_bin}",
    ])
    cmd.extend(["--filter-tcp=443", f"--hostlist={lp('list-google.txt')}"] + google_params + ["--new"])

    games_params = [games_desync, games_repeats_param]
    if provider_settings["use_fooling"] and current_mode != "Оптимизированный":
        games_params.append("--dpi-desync-fooling=ts")
    cmd.extend(["--filter-tcp=443", f"--hostlist={lp('list-games.txt')}"] + games_params + ["--new"])

    # Прочие таргеты
    targets = [
        ("list-meta.txt", "--dpi-desync=fake"),
        ("list-telegram.txt", "--dpi-desync=fake,fakedsplit"),
        ("list-tiktok.txt", "--dpi-desync=split2"),
        ("list-x.txt", "--dpi-desync=fake"),
    ]
    for hostlist, method in targets:
        cmd.extend([
            "--filter-tcp=443",
            f"--hostlist={lp(hostlist)}",
            method,
            f"--dpi-desync-repeats={max(1, base_repeats)}",
            f"--dpi-desync-fake-tls={tls_bin}",
            "--new",
        ])

    for optional in ["list-mylist.txt", "list-ip.txt"]:
        optional_path = lp(optional)
        if os.path.exists(optional_path) and os.path.getsize(optional_path) > 0:
            cmd.extend([
                "--filter-tcp=80,443" if optional == "list-ip.txt" else "--filter-tcp=443",
                f"--hostlist={optional_path}",
                "--dpi-desync=fake",
                f"--dpi-desync-repeats={base_repeats}",
                "--new",
            ])

    cmd.extend([
        "--filter-tcp=80,443",
        f"--hostlist={lp('list-general.txt')}",
        f"--hostlist-exclude={lp('list-exclude.txt')}",
        f"--ipset-exclude={lp('ipset-exclude.txt')}",
        f"--dpi-desync={base_methods[0] if base_methods else 'fake'}",
        "--dpi-desync-repeats=1",
        "--new",
        "--filter-tcp=80,443",
        f"--ipset={lp('ipset-all.txt')}",
        f"--hostlist-exclude={lp('list-exclude.txt')}",
        f"--ipset-exclude={lp('ipset-exclude.txt')}",
        f"--dpi-desync={base_methods[0] if base_methods else 'fake'}",
        "--dpi-desync-repeats=1",
        "--new",
        "--filter-udp=443",
        f"--ipset={lp('ipset-all.txt')}",
        f"--hostlist-exclude={lp('list-exclude.txt')}",
        f"--ipset-exclude={lp('ipset-exclude.txt')}",
        "--dpi-desync=fake",
        f"--dpi-desync-repeats={base_repeats}",
        f"--dpi-desync-fake-quic={quic_bin}",
    ])

    cmd = [part for part in cmd if part]

    try:
        process = subprocess.Popen(
            cmd,
            cwd=bin_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        is_running = True
        time.sleep(1)
        if process.poll() is not None:
            _, stderr = process.communicate()
            error_msg = (
                stderr.decode("utf-8", errors="ignore") if stderr else "Неизвестная ошибка"
            )
            print(f"Ошибка запуска: {error_msg}")
            notify("Ошибка запуска: проверьте логи")
            is_running = False
        else:
            notify(f"Обход активирован: {current_provider} ({current_mode}) 🚀")
            print(f"Запущено с параметрами: {' '.join(cmd[:5])}...")
    except Exception as exc:
        print(f"Ошибка запуска: {exc}")
        notify(f"Ошибка запуска: {exc}")
        is_running = False


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("500x720")
        self.resizable(False, False)
        ctk.set_appearance_mode("dark")
        base_path = get_base()

        bg_path = os.path.join(base_path, "background.png")
        if os.path.exists(bg_path):
            bg_image = Image.open(bg_path)
            self.bg_image = ctk.CTkImage(light_image=bg_image, dark_image=bg_image, size=(500, 720))
            self.bg_label = ctk.CTkLabel(self, image=self.bg_image, text="")
            self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)

        icon_path = os.path.join(base_path, "icon.ico")
        if os.path.exists(icon_path):
            self.after(200, lambda: self.iconbitmap(icon_path))

        self.missing_files = check_list_files()
        title_color = "#FF4444" if self.missing_files else "#00FF00"
        self.label = ctk.CTkLabel(self, text=APP_NAME, font=("Impact", 28, "bold"), text_color=title_color)
        self.label.pack(pady=10)

        self.tabview = ctk.CTkTabview(self, width=460, height=550)
        self.tabview.pack(pady=10, padx=20)
        self.tab_main = self.tabview.add("Основная")
        self.tab_advanced = self.tabview.add("Провайдеры")
        self.tab_service = self.tabview.add("Сервис")

        self.setup_main_tab()
        self.setup_provider_tab()
        self.setup_service_tab()

        self.status = ctk.CTkLabel(self, text="● ACTIVE", font=("Arial", 18, "bold"), text_color="green")
        self.status.pack(pady=5)
        self.protocol("WM_DELETE_WINDOW", self.hide_window)
        self.after(1000, self.auto_start)

    def setup_main_tab(self) -> None:
        self.mode_menu = ctk.CTkSegmentedButton(
            self.tab_main,
            values=["Оптимизированный", "Стандарт", "Агрессив", "Экстрим"],
            command=self.change_mode,
        )
        self.mode_menu.set("Оптимизированный")
        self.mode_menu.pack(pady=10, padx=30, fill="x")

        self.btn_start = ctk.CTkButton(self.tab_main, text="▶ ЗАПУСТИТЬ / ПЕРЕЗАГРУЗИТЬ", command=self.restart)
        self.btn_start.pack(pady=8, padx=30, fill="x")
        self.btn_stop = ctk.CTkButton(self.tab_main, text="⏹ ОСТАНОВИТЬ DPI", command=self.stop)
        self.btn_stop.pack(pady=8, padx=30, fill="x")

        self.log = ctk.CTkTextbox(self.tab_main, height=260)
        self.log.pack(pady=10, padx=20, fill="both")
        self.log.insert("0.0", "Система готова к работе.\n")
        self.log.configure(state="disabled")

    def setup_provider_tab(self) -> None:
        self.provider_menu = ctk.CTkSegmentedButton(
            self.tab_advanced,
            values=["Авто", "Ростелеком", "МТС", "Билайн", "МегаФон", "Дом.ру", "TTK"],
            command=self.change_provider,
        )
        self.provider_menu.set("Авто")
        self.provider_menu.pack(pady=10, padx=30, fill="x")

        self.settings_text = ctk.CTkTextbox(self.tab_advanced, height=220)
        self.settings_text.pack(pady=10, padx=20, fill="both")
        self.update_provider_info()

    def setup_service_tab(self) -> None:
        self.service_status_text = ctk.CTkTextbox(self.tab_service, height=160)
        self.service_status_text.pack(pady=10, padx=20, fill="x")
        self.service_status_text.insert("0.0", "Нажмите кнопку проверки статуса\n")

        self.btn_check_status = ctk.CTkButton(self.tab_service, text="🔄 Проверить статус", command=self.check_service_status)
        self.btn_check_status.pack(pady=5, padx=20, fill="x")

    def auto_start(self) -> None:
        self.log_insert("Запуск в оптимизированном режиме (Авто)...")
        threading.Thread(target=start_zapret, daemon=True).start()

    def change_mode(self, value: str) -> None:
        global current_mode
        current_mode = value
        self.log_insert(f"Режим изменён → {value}")
        self.update_provider_info()

    def change_provider(self, value: str) -> None:
        global current_provider
        current_provider = value
        self.log_insert(f"Провайдер изменён → {value}")
        self.update_provider_info()

    def update_provider_info(self) -> None:
        settings = get_provider_settings(current_provider)
        info = (
            f"Провайдер: {current_provider}\n"
            f"Обычные сайты: {', '.join(settings['general_methods'])}\n"
            f"Google/YouTube: {', '.join(settings['google_methods'])}\n"
            f"Игры: {', '.join(settings['games_methods'])}\n"
            f"Режим: {current_mode}\n"
        )
        self.settings_text.configure(state="normal")
        self.settings_text.delete("0.0", "end")
        self.settings_text.insert("0.0", info)
        self.settings_text.configure(state="disabled")

    def log_insert(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def restart(self) -> None:
        self.status.configure(text="● ACTIVE", text_color="green")
        self.log_insert(f"Запуск: {current_provider} ({current_mode})...")
        threading.Thread(target=start_zapret, daemon=True).start()

    def stop(self) -> None:
        global is_running
        kill_old_instances()
        is_running = False
        self.status.configure(text="● STOPPED", text_color="red")
        self.log_insert("Обход остановлен.")
        notify("Обход остановлен 🛑")

    def check_service_status(self) -> None:
        service_status = get_service_status()
        process_status = check_process_status()
        self.service_status_text.configure(state="normal")
        self.service_status_text.delete("0.0", "end")
        self.service_status_text.insert(
            "0.0",
            f"Служба zapret: {service_status}\n"
            f"Процесс winws_zapret.exe: {process_status}\n",
        )
        self.service_status_text.configure(state="disabled")

    def hide_window(self) -> None:
        self.withdraw()


def setup_tray(app: App) -> None:
    global icon
    base = get_base()
    icon_path = os.path.join(base, "icon.ico")
    icon1_path = os.path.join(base, "icon1.ico")
    icon2_path = os.path.join(base, "icon2.ico")

    def load_icon(path: str, fallback: tuple[int, int, int]) -> Image.Image:
        if os.path.exists(path):
            return Image.open(path)
        return Image.new("RGB", (64, 64), fallback)

    img0 = load_icon(icon_path, (0, 150, 0))
    img1 = load_icon(icon1_path, (0, 100, 0))
    img2 = load_icon(icon2_path, (150, 0, 0))

    menu = pystray.Menu(
        item("Открыть панель", app.deiconify),
        item("Перезапустить", app.restart),
        item("Остановить", app.stop),
        item("Выход", lambda: (kill_old_instances(), app.quit(), os._exit(0))),
    )
    icon = pystray.Icon("G-Zapret", img0, "Global-Zapret v5.1.5", menu)

    def animate_icon() -> None:
        while True:
            if is_running:
                icon.icon = img0
                time.sleep(0.5)
                if is_running:
                    icon.icon = img1
                time.sleep(0.5)
            else:
                icon.icon = img2
                time.sleep(1)

    threading.Thread(target=animate_icon, daemon=True).start()
    icon.run()


def main() -> None:
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            sys.executable,
            " ".join(sys.argv),
            None,
            1,
        )
        return
    app = App()
    threading.Thread(target=setup_tray, args=(app,), daemon=True).start()
    app.mainloop()


if __name__ == "__main__":
    main()
