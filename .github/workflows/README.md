# Тест СП 53-101-98 — портативное Windows-приложение

Десктоп-GUI вместо локального сайта. Один `.exe` + файлы данных рядом (json, png).  
Результаты и блокировка пишутся в папку с exe — удобно на сетевой шаре.

## Структура

```
main.py
app/          # config, storage, logic
ui/           # экраны: старт, тест, результат, админка
build.spec
requirements.txt
.github/workflows/build-windows.yml
```

## Локальная разработка (нужен Python 3.11+)

1. Скопируйте рядом с `main.py` данные из старого сайта:
   - `questions.json`, `results.json`, `lock.json`
   - `1.png` … `37.png`
2. Установка:
   ```bash
   pip install -r requirements.txt
   ```
3. Запуск:
   ```bash
   python main.py
   ```

## Сборка exe локально

```bash
pip install -r requirements.txt pyinstaller
pyinstaller build.spec --noconfirm --clean
```

Готовый файл: `dist/Тест_СП_53.exe`.  
Положите его в папку с `questions.json`, `results.json`, `lock.json` и png.

## Сборка через GitHub Actions

1. Создайте репозиторий на GitHub и залейте этот проект.
2. Откройте вкладку **Actions** → workflow **Build Windows EXE**.
3. Либо дождитесь автозапуска по push в `main`/`master`, либо нажмите **Run workflow**.
4. После успеха скачайте artifact **SP53-Test-Windows**.
5. Извлеките `Тест_СП_53.exe` и положите в папку с данными на сетевом диске.

## Важно про пути

При запуске из PyInstaller `frozen` приложение использует **папку, где лежит exe**  
(`os.path.dirname(sys.executable)`), а не `sys._MEIPASS`.  
Поэтому `results.json` и `lock.json` общие для всех ПК, если exe на шаре.

## Функционал

- Старт: ФИО, часть 1/2, блокировка `lock.json` (~45 мин)
- Тест: таймер (30/50 мин), прогресс, картинки, время на каждый вопрос
- Результат: % и разбор ошибок
- Админка (пароль `admin`): сводка, сложные вопросы, сотрудники, детализация, CSV «;» UTF-8 BOM, очистка

## Смена пароля админа

Файл `app/config.py`, константа `ADMIN_PASSWORD`. После смены пересоберите exe.
