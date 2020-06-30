import os
import logging
from tkinter import *
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog
from threading import Thread
from src.callback import Callback
from src.save_image import ImageDownloader
from src import pbm_version


def show_message_box_on_exception(exc: Exception):
    messagebox.showerror(title='An exception occurred',
                         message='An exception occurred:\n{}'
                                 '\n\nDetails:\n{}'
                                 '\n\nPlease report the issue on GitHub'.format(exc, exc.args))

    exit(1)


class PDBApp(Frame):
    def __init__(self, master):
        Frame.__init__(self, master)
        master.title('Pybimun v{}'.format(pbm_version))
        style = ttk.Style()
        self._style = StringVar()
        if 'vista' in style.theme_names():
            self._style.set('vista')
        else:
            self._style.set('default')
        style.theme_use(self._style.get())

        # Layout configuration
        columns = 0
        while columns < 10:
            master.columnconfigure(columns, weight=1)
            columns += 1
        rows = 0
        while rows < 5:
            w = 1 if rows != 3 else 5
            master.rowconfigure(rows, weight=w)
            rows += 1

        # First line
        self._label_url = ttk.Label(master, text='URL')
        self._label_url.grid(row=0, column=0, padx=2, pady=2, sticky=W+E)
        self._entry_url = ttk.Entry(master)
        self._entry_url.grid(row=0, column=1, padx=2, pady=2, columnspan=8, sticky=W+E)
        self._btn_download = ttk.Button(master, text='Download', command=self.download)
        self._btn_download.grid(row=0, column=9, columnspan=1, rowspan=3, sticky=W+E,
                                padx=2, pady=2, ipady=28)

        # Second line
        self._label_folder = ttk.Label(master, text='Folder')
        self._label_folder.grid(row=1, column=0, padx=2, sticky=W+E)
        self._entry_folder = ttk.Entry(master)
        self._entry_folder.grid(row=1, column=1, padx=2, columnspan=7, sticky=W+E)
        self._btn_nav = ttk.Button(master, text='...', command=self.browse_directory)
        self._btn_nav.grid(row=1, column=8, padx=2, pady=2, sticky=W+E)

        # Third line
        self._label_name = ttk.Label(master, text='Filename')
        self._label_name.grid(row=2, column=0, padx=2, sticky=W+E)
        self._entry_name = ttk.Entry(master)
        self._entry_name.grid(row=2, column=1, padx=2, pady=2, columnspan=8, sticky=W+E)

        # Fourth line
        self._progress_bar = ttk.Progressbar(master, orient='horizontal', mode='determinate')
        self._progress_bar.grid(row=3, column=0, columnspan=10, sticky=W+E+N+S, padx=2, pady=2)
        self._progress_bar["maximum"] = 100

        # Fifth line
        self._text = Text(master)
        self._text.grid(row=4, column=0, columnspan=10, sticky=W+E+N+S, padx=2, pady=2)
        self._text.configure(state=DISABLED)

        self._logger = Log2Text(self._text)
        logging.getLogger().setLevel(logging.INFO)
        logging.getLogger().addHandler(self._logger)

        # Utilities
        self._dl = ImageDownloader(self._entry_url.get(), os.path.join(self._entry_folder.get(),
                                                                       self._entry_name.get()))
        self._dl_thread = Thread(target=None)
        self._callback = Callback(self._progress_bar)

        # Launch background task
        self.reset_buttons()

    def reset_buttons(self):
        if not self._dl_thread.is_alive():
            self._switch_action(False)
            self._callback.reset()
        self.after(100, self.reset_buttons)

    def browse_directory(self):
        cur_dir = self._entry_folder.get()
        initial_dir = cur_dir if os.path.exists(cur_dir) else os.path.expanduser('~')
        directory = filedialog.askdirectory(title='Select directory',
                                            initialdir=initial_dir)
        if directory:
            self._entry_folder.delete(0, END)
            self._entry_folder.insert(0, directory)

    def _clean_text_box(self):
        try:
            self._text.configure(state=NORMAL)
            self._text.delete('1.0', END)
            self._text.configure(state=DISABLED)
        except TclError as exc:
            logging.warning('Can\'t clean text ({})'.format(exc))

    def _update_dl_with_fields(self):
        self._dl.url(self._entry_url.get())
        self._dl.output(os.path.join(self._entry_folder.get(), self._entry_name.get()))

    def _switch_action(self, action: bool):
        state_f_dl = DISABLED if action else NORMAL
        self._btn_download.configure(state=state_f_dl)

    def download(self):
        self._clean_text_box()
        if not self._entry_folder.get():
            logging.error("Folder can't be empty!")
            return
        if not self._entry_name.get():
            logging.error("Filename can't be empty!")
            return
        if self._entry_name.get()[-4:] != ".jpg":
            logging.error("Filename should be a JPG!")
            return
        if "bibliotheques-specialisees.paris.fr" not in self._entry_url.get():
            logging.error("URL must be from bibliotheques-specialisees.paris.fr")
            return
        self._update_dl_with_fields()
        logging.info("Start download")
        self._dl_thread = Thread(target=self._dl.download,
                                 kwargs={'cb': self._callback})
        self._switch_action(True)
        self._dl_thread.start()


class Log2Text(logging.Handler):
    def __init__(self, text):
        logging.Handler.__init__(self)
        self.setLevel(logging.INFO)
        f = logging.Formatter('[%(asctime)s][%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S')
        self.setFormatter(f)
        self._text = text

    def emit(self, record):
        formatted_message = self.format(record)
        self._text.configure(state=NORMAL)
        self._text.insert(END, formatted_message)
        self._text.insert(END, '\n')
        self._text.configure(state=DISABLED)
        self._text.see(END)


def main():
    root = Tk()
    root.resizable(0, 0)
    icon_path = 'pbd_icon.ico'
    if not os.path.isfile(icon_path):
        icon_path = '../img/pbd_icon.ico'
    if os.path.isfile(icon_path):
        root.iconbitmap(icon_path)

    try:
        PDBApp(root)
        root.mainloop()
    except Exception as exc:
        show_message_box_on_exception(exc)
    return 0


if __name__ == '__main__':
    main()
