# Castorice AI 桌面预览版

## 安装版

运行 `desktop-release/Castorice-AI-0.1.0-Setup.exe`，按向导选择安装位置。支持桌面与开始菜单快捷方式、系统应用列表卸载；卸载保留用户数据。运行库只在安装时解压，日常启动不重复解压。安装版仍未签名，AI 配置、数据目录与预览版一致。

`npm run pack` 默认生成安装版，`npm run pack:portable` 生成单文件便携版。

2026-11-03：已生成 `desktop-release/Castorice-AI-0.1.0-preview.exe`，约 226.4 MiB。前端 30 项、后端 11 项现有检查通过；开发外壳和打包目录 exe 的自动启动检查均通过，退出后后台端口已关闭。没有调用真实生成模型。单文件便携版每次启动需先解压后台和运行库，启动速度比打包目录 exe 慢。

保持现有网页布局。Python 后端、前端资源与 Electron 一起打包；不内置模型权重或私人 API Key。预览版未签名。

最终单文件便携 exe 也已通过自动启动验证：成功解压并加载页面、启动后台、退出。第一次实测解压等待较长；需要快速体验时，可运行 `desktop-release/win-unpacked/Castorice AI.exe`，该文件必须与整个 win-unpacked 目录一起保留。

启动前配置 `DASHSCOPE_API_KEY` 环境变量，或者在 `%APPDATA%/Castorice AI/.env` 中填写 `DASHSCOPE_API_KEY=你的密钥`。不要将该文件分享。现有电脑若已配置环境变量可直接使用。

上传文件、索引、浏览器历史与后台日志保存在用户数据目录，与网页版各自独立。关闭窗口会停止本应用启动的后台；不会停止开发服务器。后台使用随机端口，界面使用本机 18573 端口；端口被占用会提示错误。

构建：先在 `castorice_vue` 执行 `npm ci`、`npm run build`，安装 Python 后端依赖及 PyInstaller，再在项目根目录执行 `desktop/build.ps1`。首次需在 desktop 下执行 `npm ci` 安装桌面依赖。

开发启动：构建一次后台和网页后，在 desktop 下执行 `npm start`。当前预览加载构建后的网页；网页源码修改后重新运行前端 build、重启窗口即可，不需要重新生成整个便携 exe。

OCR 仍依赖额外安装的 Tesseract 与语言包。AI 服务需要网络和有效额度。Codex 替换尚未接入。首次不做真实模型生成测试，尤其不测试收费视频。
