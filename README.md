# BMIcalc - 身体质量指数计算器

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![PyQt5](https://img.shields.io/badge/PyQt5-5.15+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Version](https://img.shields.io/badge/Version-0.0.1-orange.svg)

**bjp6272 出品**

*A simple, cross-platform BMI Calculator*

</div>

---

## 📖 简介

BMIcalc 是一款简洁、易用的身体质量指数（BMI）计算器。

### 主要特点

- 🌐 **多语言支持** - 支持 6 种语言：简体中文、English、한국어、日本語、Deutsch、Français
- 📊 **科学标准** - 严格遵循中国卫生行业标准
  - 学龄前儿童 (0-6岁): WS/T 423-2022
  - 学龄儿童青少年 (7-18岁): WS/T 586-2018
  - 成人 (18岁及以上): WS/T 428-2013
- 🎨 **现代化界面** - 简洁美观的用户界面
- 💻 **跨平台** - 支持 Windows、macOS、Linux

---

## 🖥️ 系统要求

- Python 3.8 或更高版本
- PyQt5 5.15 或更高版本

---

## 🚀 安装与运行

### 方式一：从源码运行

```bash
# 克隆仓库
git clone https://github.com/bjp6272/BMIcalc.git
cd BMIcalc

# 安装依赖
pip install PyQt5

# 运行程序
python bmi_app.py
```

### 方式二：下载预编译版本

前往 [Releases](https://github.com/bjp6272/BMIcalc/releases) 页面下载对应平台的压缩包，解压后直接运行可执行文件。

---

## 📖 使用说明

1. **选择年龄段** - 根据实际年龄选择对应区间
2. **选择性别** - 男/女（部分年龄段需要）
3. **输入身高** - 单位为厘米 (cm)
4. **输入体重** - 单位为公斤 (kg)
5. **点击计算** - 查看 BMI 结果及健康评估

---

## 🌐 多语言切换

点击界面右下角「选项」按钮，可以随时切换界面语言。

支持的语言：

| 语言代码 | 语言名称 | 状态 |
|----------|----------|------|
| zh-CN | 简体中文 | ✅ |
| en-US | English | ✅ |
| ko-KR | 한국어 | ✅ |
| ja-JP | 日本語 | ✅ |
| de-DE | Deutsch | ✅ |
| fr-FR | Français | ✅ |

---

## 🛠️ 构建打包

### Windows

```bash
pip install pyinstaller
pyinstaller --onefile --windowed bmi_app.py
```

### macOS / Linux

```bash
pip install pyinstaller
pyinstaller --onefile bmi_app.py
```

---

## 📁 项目结构

```
BMIcalc/
├── bmi_app.py              # 主程序
├── translations/           # 多语言文件
│   ├── zh-CN-bmi.ini       # 简体中文
│   ├── en-US-bmi.ini       # 英语
│   ├── ja-JP-bmi.ini       # 日语
│   ├── ko-KR-bmi.ini       # 韩语
│   ├── de-DE-bmi.ini       # 德语
│   └── fr-FR-bmi.ini       # 法语
├── README.md               # 说明文档
└── LICENSE                # MIT 许可证
```

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源许可。

---

## 👤 作者

- **baijianpeng**
- Email: baijianpeng@qq.com

---

## 🙏 致谢

- 基于 [PyQt5](https://pypi.org/project/PyQt5/) 框架开发
- 严格遵循《体重管理指导原则（2024年版）》及中国卫生行业标准

---

<div align="center">

**Made with ❤️ by bjp6272**

</div>
