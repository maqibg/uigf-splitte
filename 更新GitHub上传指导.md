# GitHub 发布新版本流程指南

本文档用于指导如何将本地的项目更新打包并发布到 GitHub Releases。

## 步骤一：打包生成可执行文件

首先，我们需要为不同平台（Windows, macOS）生成独立的可执行文件。

1.  **确保 `PyInstaller` 已安装**:
    ```bash
    pip install pyinstaller
    ```

2.  **执行打包命令**:
    打开项目根目录的终端，运行以下命令来创建一个单文件、无控制台窗口的应用程序。

    ```bash
    pyinstaller --onefile --windowed --name="UIGF-SRGF处理工具-v1.1" main.py
    ```
    - `--onefile`: 将所有内容打包到一个可执行文件中。
    - `--windowed`: 在Windows上运行时不显示命令行窗口。
    - `--name`: 指定输出文件的名称，建议包含版本号。

3.  **找到生成的文件**:
    打包成功后，可执行文件会位于项目根目录下的 `dist` 文件夹中。例如 `dist/UIGF-SRGF处理工具-v1.1.exe`。

## 步骤二：在 GitHub 上创建新的 Release

1.  **打开项目 GitHub 页面**：
    访问 `https://github.com/maqibg/yunzai-uigf-splitte`

2.  **进入 Releases 页面**：
    在主页右侧栏找到并点击 "Releases"。

3.  **创建新版本 (Draft a new release)**：
    点击 "Draft a new release" 按钮。

4.  **填写版本信息**：
    - **Tag version (版本标签)**: 输入新的版本号，例如 `v1.1.0`。如果标签不存在，GitHub 会提示你基于主分支创建一个新的。
    - **Release title (发布标题)**: 输入一个清晰的标题，例如 `v1.1.0 - UI重构与功能增强`。
    - **Describe this release (描述)**:
        - 将 `RELEASE_NOTES.md` 文件中对应版本的更新内容复制到这里。
        - 这能让用户清晰地了解本次更新带来了哪些变化。

5.  **上传附件 (Attach binaries)**：
    - 将 `dist` 文件夹中生成的可执行文件（如 `.exe` 文件）拖拽到 "Attach binaries by dropping them here or selecting them." 区域。
    - 如果有为其他操作系统（如 macOS）打包的文件，也一并上传。

6.  **发布版本 (Publish release)**：
    - 确认所有信息无误后，点击 "Publish release" 按钮。
    - 如果还不确定，可以点击 "Save draft" 先保存为草稿。

## 步骤三：更新代码到主分支

最后，确保所有本地的代码和文档更新都已推送到 GitHub 仓库。

1.  **检查本地修改**:
    ```bash
    git status
    ```
    确保 `main.py`, `README.md`, `RELEASE_NOTES.md` 等文件的修改都已包含。

2.  **添加并提交修改**:
    ```bash
    git add .
    git commit -m "feat: Release v1.1.0 - UI overhaul and new features"
    ```
    建议使用清晰的 commit message。

3.  **推送到远程仓库**:
    ```bash
    git push origin main
    ```

完成以上步骤后，你的项目新版本就成功发布了，并且代码也同步到了最新状态。