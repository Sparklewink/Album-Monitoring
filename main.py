import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import requests
import threading
import time
from just_playback import Playback  # <--- 修改1：导入 Playback
import json
import os
from netease_crypto import encrypted_request

# --- 配置文件名 ---
CONFIG_FILE = 'config.json'


class AlbumMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("天枢监控")

        try:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tx.ico')
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass

        self.config = self.load_config()

        geometry = self.config.get('geometry', '620x760+100+100')
        self.root.geometry(geometry)
        self.root.resizable(True, True)

        self.monitoring_thread = None
        self.is_monitoring = False
        self.playback_obj = None

        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- GUI 输入框 ---
        ttk.Label(main_frame, text="代理地址:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.proxy_entry = ttk.Entry(main_frame, width=65)
        self.proxy_entry.insert(0, self.config.get('proxy', "http://127.0.0.1:10808"))
        self.proxy_entry.grid(row=0, column=1, sticky=tk.W)

        ttk.Label(main_frame, text="专辑ID:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.album_id_entry = ttk.Entry(main_frame, width=65)
        self.album_id_entry.insert(0, self.config.get('album_id', "280682247"))
        self.album_id_entry.grid(row=1, column=1, sticky=tk.W)

        ttk.Label(main_frame, text="Cookie:").grid(row=2, column=0, sticky=tk.NW, pady=5)
        self.cookie_text = tk.Text(main_frame, height=5, width=65, wrap=tk.WORD)
        self.cookie_text.insert("1.0", self.config.get('cookie', ''))
        self.cookie_text.grid(row=2, column=1, sticky=tk.W)

        ttk.Label(main_frame, text="检测间隔 (ms):").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.interval_entry = ttk.Entry(main_frame, width=25)
        self.interval_entry.insert(0, self.config.get('interval', "3000"))
        self.interval_entry.grid(row=3, column=1, sticky=tk.W)

        ttk.Label(main_frame, text="预警阈值 (张):").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.threshold_entry = ttk.Entry(main_frame, width=25)
        self.threshold_entry.insert(0, self.config.get('threshold', "100"))
        self.threshold_entry.grid(row=4, column=1, sticky=tk.W)

        ttk.Label(main_frame, text="预警声音:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.sound_path_label = ttk.Label(main_frame, text=self.config.get('sound_path', "未选择文件"),
                                          foreground="black" if self.config.get('sound_path') else "gray")
        self.sound_path_label.grid(row=5, column=1, sticky=tk.W)
        self.sound_browse_button = ttk.Button(main_frame, text="选择...", command=self.browse_sound_file)
        self.sound_browse_button.grid(row=5, column=2, sticky=tk.E)

        ttk.Label(main_frame, text="Server酱 Token:").grid(row=6, column=0, sticky=tk.W, pady=5)
        self.server_chan_token_entry = ttk.Entry(main_frame, width=65)
        self.server_chan_token_entry.insert(0, self.config.get('server_chan_token', ''))
        self.server_chan_token_entry.grid(row=6, column=1, sticky=tk.W)

        # --- 按钮和日志 ---
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=7, column=1, pady=20, sticky=tk.W)
        self.start_button = ttk.Button(button_frame, text="开始监控", command=self.start_monitoring)
        self.start_button.pack(side=tk.LEFT, padx=5)
        self.stop_button = ttk.Button(button_frame, text="停止监控", command=self.stop_monitoring, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        log_frame = ttk.LabelFrame(main_frame, text="执行日志")
        log_frame.grid(row=8, column=0, columnspan=3, sticky="nsew")
        main_frame.grid_rowconfigure(8, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)

        self.log_text = tk.Text(log_frame, wrap=tk.WORD, bg="black", fg="lime green")
        self.log_text.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)

        self.log("欢迎使用天枢监控")
        self.log("配置已自动加载。")

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_config(self):
        config_data = {
            'geometry': self.root.geometry(), 'proxy': self.proxy_entry.get().strip(),
            'album_id': self.album_id_entry.get().strip(), 'cookie': self.cookie_text.get("1.0", tk.END).strip(),
            'interval': self.interval_entry.get().strip(), 'threshold': self.threshold_entry.get().strip(),
            'sound_path': self.sound_path_label.cget("text") if self.sound_path_label.cget(
                "text") != "未选择文件" else "",
            'server_chan_token': self.server_chan_token_entry.get().strip()
        }
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
            self.log("配置已成功保存到 config.json")
        except IOError:
            self.log("错误：无法写入配置文件 config.json")

    def on_closing(self):
        if self.is_monitoring:
            if messagebox.askyesno("退出确认", "监控仍在运行中，确定要退出吗？"):
                self.stop_monitoring()
                self.save_config()
                self.root.destroy()
        else:
            self.save_config()
            self.root.destroy()

    def browse_sound_file(self):
        filepath = filedialog.askopenfilename(
            title="选择一个音频文件",
            filetypes=(("音频文件", "*.wav *.mp3 *.ogg *.flac"), ("所有文件", "*.*"))
        )
        if filepath:
            self.sound_path_label.config(text=filepath, foreground="black")

    def log(self, message):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

    def start_monitoring(self):
        if self.is_monitoring: return

        proxy_str = self.proxy_entry.get().strip()
        album_id = self.album_id_entry.get().strip()
        cookie = self.cookie_text.get("1.0", tk.END).strip()

        if not all([album_id.isdigit(), cookie]):
            messagebox.showerror("输入错误", "专辑ID 和 Cookie 均不能为空！")
            return

        try:
            interval = int(self.interval_entry.get().strip())
            threshold = int(self.threshold_entry.get().strip())
        except ValueError:
            messagebox.showerror("输入错误", "检测间隔和预警阈值必须是数字！")
            return

        self.is_monitoring = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.log(f"监控已开始，目标专辑ID: {album_id}")
        if proxy_str: self.log(f"使用代理: {proxy_str}")

        self.monitoring_thread = threading.Thread(
            target=self.monitoring_loop, args=(album_id, cookie, proxy_str, interval, threshold), daemon=True
        )
        self.monitoring_thread.start()

    def stop_monitoring(self):
        if not self.is_monitoring: return
        self.is_monitoring = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        # 停止可能正在播放的音乐
        if self.playback_obj:
            try:
                self.playback_obj.stop()
            except Exception:
                pass  # 忽略停止时可能发生的错误
        self.log("监控已手动停止。")

    def monitoring_loop(self, album_id, cookie, proxy_str, interval, threshold):
        api_url = "https://music.163.com/weapi/vipmall/albumproduct/sales/v2"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
            'Referer': f'https://music.163.com/store/newalbum/detail?id={album_id}',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Cookie': cookie
        }

        original_post_data = {
            'albumId': album_id
        }

        proxies = {'http': proxy_str, 'https': proxy_str} if proxy_str else None

        while self.is_monitoring:
            try:
                encrypted_data = encrypted_request(original_post_data)

                response = requests.post(api_url, headers=headers, data=encrypted_data, proxies=proxies, timeout=20)
                response.raise_for_status()
                json_data = response.json()

                if json_data.get('code') == 200 and 'data' in json_data and isinstance(json_data['data'],
                                                                                       dict) and 'sales' in json_data[
                    'data']:
                    current_sales = json_data['data']['sales']
                    self.log(f"成功获取销量: {current_sales} 张")

                    if current_sales >= threshold:
                        self.log(f"警报！销量 ({current_sales}) 已达到阈值 ({threshold})！")
                        self.trigger_alert(current_sales, threshold)
                        # trigger_alert后监控会自动停止，所以声音会自动播放
                        self.stop_monitoring()
                        break
                else:
                    self.log(f"API返回数据异常或无权限: {json_data}")

            except requests.exceptions.JSONDecodeError:
                self.log("错误: 服务器返回内容非JSON格式, 鉴权或代理失败。")
            except requests.exceptions.ProxyError as e:
                self.log(f"代理错误: 无法连接到代理服务器 {proxy_str}。")
            except requests.RequestException as e:
                self.log(f"网络请求错误: {e}")
            except Exception as e:
                self.log(f"发生未知错误: {e}")

            if not self.is_monitoring:
                break

            time.sleep(interval / 1000)

    def trigger_alert(self, current_sales, threshold):
        alert_title = "专辑销量预警！"
        alert_message = f"专辑销量已达到 {current_sales} 张，超过预警阈值 {threshold}！"

        sound_path = self.sound_path_label.cget("text")
        if sound_path != "未选择文件" and os.path.exists(sound_path):
            try:
                self.log(f"正在播放预警声音: {os.path.basename(sound_path)}")
                # just_playback 自动在后台线程播放
                self.playback_obj = Playback(sound_path)
                self.playback_obj.play()
            except Exception as e:
                self.log(f"播放声音失败: {e}。请确保文件格式受支持。")
        elif sound_path != "未选择文件":
            self.log(f"播放声音失败：未找到文件 {sound_path}")
        # --- 声音播放逻辑结束 ---

        server_chan_token = self.server_chan_token_entry.get().strip()
        if server_chan_token:
            try:
                server_chan_url = f"https://sctapi.ftqq.com/{server_chan_token}.send"
                payload = {'title': alert_title, 'desp': alert_message}
                requests.post(server_chan_url, data=payload)
                self.log("已发送微信Server酱通知。")
            except Exception as e:
                self.log(f"发送微信通知失败: {e}")

        # 弹窗
        messagebox.showwarning(alert_title, alert_message)


if __name__ == "__main__":
    root = tk.Tk()
    app = AlbumMonitorApp(root)
    root.mainloop()