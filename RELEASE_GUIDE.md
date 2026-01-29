# Пошаговая инструкция: GitHub Release и GitHub Pages

Инструкция по публикации приложения ChatList в **GitHub Release** (артефакты сборки) и развёртыванию **лендинга** на **GitHub Pages**.

---

## Часть 1. Подготовка репозитория

### 1.1. Замените плейсхолдеры на ваш репозиторий

В файлах проекта замените `YOUR_USERNAME` и `YOUR_REPO` (или `chatlist`) на реальные значения:

- **install.iss** — строка `#define MyAppURL "https://github.com/..."`  
  Пример: `https://github.com/YourUsername/ChatList`
- **docs/index.html** — все ссылки вида `https://github.com/YOUR_USERNAME/YOUR_REPO`
- В этой инструкции везде подставляйте ваш логин и имя репозитория.

### 1.2. Версия приложения

Версия берётся из **version.py** (`__version__`). Для нового релиза:

1. Отредактируйте `version.py`, например: `__version__ = "1.0.1"`
2. Закоммитьте изменение и запушьте в `main`.

---

## Часть 2. GitHub Release (сборка и публикация артефактов)

### 2.1. Включение workflow

В репозитории уже есть файл:

```
.github/workflows/release.yml
```

Он запускается при **создании тега** вида `v*` (например, `v1.0.0`).

### 2.2. Создание релиза по шагам

1. **Убедитесь, что в `version.py` указана нужная версия** (например, `1.0.0`).

2. **Закоммитьте и запушьте все изменения в ветку `main`:**

   ```powershell
   git add -A
   git status
   git commit -m "Подготовка к релизу 1.0.0"
   git push origin main
   ```

3. **Создайте тег, совпадающий с версией в `version.py`:**

   ```powershell
   git tag v1.0.0
   git push origin v1.0.0
   ```

4. **Дождитесь выполнения workflow:**
   - Откройте репозиторий на GitHub → вкладка **Actions**.
   - Запустится workflow **Release** (триггер — push тега).
   - Дождитесь зелёного статуса.

5. **Проверьте Release:**
   - Вкладка **Releases** (справа от Code).
   - Должна появиться запись для тега `v1.0.0` с прикреплёнными файлами:
     - `ChatList-1.0.0.exe` — портативная версия
     - `ChatList-1.0.0-setup.exe` — установщик Windows

### 2.3. Если сборка упала

- Откройте упавший run в **Actions** и посмотрите логи шага с ошибкой.
- Частые причины: несовпадение версии в теге и в `version.py`, ошибки PyInstaller или Inno Setup в workflow.
- После исправлений создайте новый тег (например, `v1.0.1`) и снова выполните `git push origin v1.0.1`.

### 2.4. Ручная сборка (без тега)

Для локальной проверки перед тегом:

```powershell
.\build.ps1
.\install.ps1
```

Артефакты: `dist\ChatList-<version>.exe` и `install\ChatList-<version>-setup.exe`.

---

## Часть 3. GitHub Pages (лендинг)

### 3.1. Включение Pages

1. На GitHub откройте репозиторий → **Settings** → **Pages**.
2. В блоке **Build and deployment**:
   - **Source:** выберите **GitHub Actions**.

После этого Pages будет собираться workflow'ом, а не веткой/папкой по умолчанию.

### 3.2. Файлы для лендинга

- **docs/index.html** — одностраничный лендинг с описанием ChatList и ссылками на скачивание.
- Workflow **.github/workflows/pages.yml** при пуше в `main` публикует содержимое папки **docs** на GitHub Pages.

### 3.3. Публикация лендинга

1. Убедитесь, что в репозитории есть папка **docs** и файл **docs/index.html** (они уже добавлены в шаблонах).
2. При необходимости замените в **docs/index.html** плейсхолдеры:
   - `YOUR_USERNAME` / `YOUR_REPO` на ваш логин и имя репозитория.
3. Закоммитьте и запушьте в `main`:

   ```powershell
   git add docs/
   git add .github/workflows/pages.yml
   git commit -m "Добавлен лендинг для GitHub Pages"
   git push origin main
   ```

4. Дождитесь завершения workflow **Pages** во вкладке **Actions**.
5. Сайт будет доступен по адресу:
   ```
   https://YOUR_USERNAME.github.io/YOUR_REPO/
   ```
   (иногда с задержкой 1–2 минуты).

### 3.4. Обновление лендинга

Просто меняйте **docs/index.html** (или другие файлы в **docs**), коммитьте и пушите в `main`. После успешного run workflow страница обновится.

---

## Часть 4. Чек-лист перед первым релизом

- [ ] В **install.iss** и **docs/index.html** указан правильный URL репозитория.
- [ ] В **version.py** указана версия, с которой хотите выпустить релиз.
- [ ] Все изменения закоммичены и запушены в `main`.
- [ ] В **Settings → Pages** выбран источник **GitHub Actions**.
- [ ] Создан тег `v<версия>` (например, `v1.0.0`) и выполнен `git push origin v1.0.0`.
- [ ] В **Actions** workflow Release завершился успешно.
- [ ] Во вкладке **Releases** есть новый релиз с exe и setup.exe.
- [ ] Workflow Pages выполнился, лендинг открывается по `https://YOUR_USERNAME.github.io/YOUR_REPO/`.

---

## Краткая шпаргалка команд

```powershell
# Обновить версию в version.py, затем:
git add -A
git commit -m "Версия 1.0.1"
git push origin main

# Создать и отправить тег (запустит Release workflow)
git tag v1.0.1
git push origin v1.0.1
```

После этого новый релиз появится в **Releases**, а лендинг обновится при следующем пуше в `main` (если меняли **docs/**).
