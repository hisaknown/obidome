# Obidome

> **A highly customizable system monitor that lives in your Windows 11 taskbar.**

![Python Version](https://img.shields.io/badge/python-3.13%2B-blue?style=flat-square&logo=python)
![Platform](https://img.shields.io/badge/platform-Windows%2011-0078D6?style=flat-square&logo=windows)
![Code Style](https://img.shields.io/badge/code%20style-ruff-000000?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)

---

## Overview

**Obidome** is a system monitor designed specifically for Windows 11. Unlike bulky desktop widgets, Obidome integrates directly into the `Shell_TrayWnd` (the taskbar), ensuring your system stats are always visible without cluttering your screen.

It leverages the power of Qt (PySide6) for rendering and supports HTML-like styling, giving you complete control over how your system metrics look.

## Features

* **Taskbar Integration:** Seamlessly overlays on the Windows 11 taskbar.
* **Real-Time Monitoring:** Accurate CPU and RAM usage stats via `psutil`.
* **Visual History:** Beautiful sparkline graphs with customizable gradients and line styles.
* **Fully Customizable:** Define your own layout using Qt-flavored HTML and stylesheet.
* **Lazy Evaluation:** Efficient system resource usage; metrics are fetched only when needed for display.
* **Extensible:** Display custom shell command outputs directly in the taskbar.

## Installation and Usage

### Releases
Download the latest release from the [Releases](https://github.com/hisaknown/obidome/releases) page.

### Using uv
Obidome is built with modern Python tooling. We recommend using [uv](https://github.com/astral-sh/uv) for the best experience.

1.  Clone the repository:
    ```bash
    git clone https://github.com/hisaknown/obidome.git
    cd obidome
    ```

2.  Install dependencies:
    ```bash
    uv sync
    ```

3. Run Obidome:
    ```bash
    uv run obidome
    ```

Once running, you will see the CPU and RAM stats appear in your taskbar.
Right-click the stats or task tray icon to access the `Settings` or `Quit`.

## Configuration

Obidome is configured via a YAML file. You can access the settings via the GUI or edit the file directly at:
`%LOCALAPPDATA%\obidome\obidome\settings.yaml`

### Example Configuration

```yaml
refresh_interval_msec: 1000
margin_right: 10
container_stylesheet: |
  font-family: 'Consolas', 'monospace';
  font-size: 14px;
  padding: 0px;

cpu_percent_plot_settings:
  line_color: "#00ff00"
  fill_style: gradient
  fill_color: "#00ff00"

ram_percent_plot_settings:
  line_color: "#4499ff"
  fill_style: gradient
  fill_color: "#4499ff"

custom_keys:
  gpu_temp: "nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader"

info_label: |
  <table width="100%" cellspacing="0" cellpadding="0">
      <tr style="background-image: url({cpu_percent_plot}); background-size: contain;">
          <td align="right" style="color: #aaaaaa; padding-right: 4px;">CPU:</td>
          <td align="left" style="color: #ffffff;">{cpu_percent:4.1f}%</td>
          <td><img src="{cpu_percent_plot}" width="25" height="15"></td>
      </tr>
      <tr>
          <td align="right" style="color: #aaaaaa; padding-right: 4px;">RAM:</td>
          <td align="left" style="color: #ffffff;">{ram_percent:4.1f}%</td>
          <td><img src="{ram_percent_plot}" width="25" height="15"></td>
      </tr>
      <tr>
          <td align="right" style="color: #aaaaaa; padding-right: 4px;">GPU:</td>
          <td align="left" style="color: #ffffff;">{gpu_temp}°C</td>
          <td></td>
      </tr>
  </table>
```

### Available Template Keys

Use these placeholders in your `info_label` HTML template. They will be replaced with real-time values.

#### CPU
*   `{cpu_percent}`: Current CPU usage percentage (float).
*   `{cpu_percent_plot}`: Base64-encoded sparkline image source (string).
*   `{cpu_demanding_process}`: Name of the process using the most CPU (requires Admin).
*   `{cpu_demanding_process_cpu_percent}`: CPU usage of the most demanding process (requires Admin).

#### RAM
*   `{ram_percent}`: Current RAM usage percentage (float).
*   `{ram_percent_plot}`: Base64-encoded sparkline image source (string).
*   `{ram_used_gb}`: Used RAM in Gigabytes (float).
*   `{ram_used_mb}`: Used RAM in Megabytes (float).
*   `{ram_total_gb}`: Total system RAM in Gigabytes (float).
*   `{ram_total_mb}`: Total system RAM in Megabytes (float).

#### Custom
*   `{custom_key_name}`: The output of the shell command defined in `custom_keys`.

## Development

This project uses `uv` for dependency management and `ruff` for code quality.

### Setup
```bash
uv sync --group dev
```

### Linting & Formatting
```bash
uv run ruff check .
uv run ruff format .
```

### Type Checking
```bash
uv run pyright src
```

## See also
* [TrafficMonitor](https://github.com/zhongyang219/TrafficMonitor)
    * Obidome is heavily inspired by TrafficMonitor, a popular system monitor on taskbar.
