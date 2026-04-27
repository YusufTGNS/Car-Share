from .ui.main_window import MainWindow


def run() -> None:
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    run()

