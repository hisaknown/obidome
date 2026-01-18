# Obidome

<p align="center">
    <img src="https://github.com/hisaknown/obidome/raw/refs/heads/main/src/obidome/res/icon.svg" width="128" height="128" alt="Obidome Icon">
</p>

> **A highly customizable system monitor that lives in your Windows 11 taskbar.**

![Python Version](https://img.shields.io/badge/python-3.13%2B-blue?style=flat-square&logo=python)
![Platform](https://img.shields.io/badge/platform-Windows%2011-0078D6?style=flat-square&logo=windows)
![Code Style](https://img.shields.io/badge/code%20style-ruff-000000?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)

---

## Overview

**Obidome** is a system monitor designed specifically for Windows 11. Unlike bulky desktop widgets, Obidome integrates directly into the `Shell_TrayWnd` (the taskbar), ensuring your system stats are always visible without cluttering your screen.

It leverages the power of Qt (PySide6) for rendering and supports HTML-like styling, giving you complete control over how your system metrics look.

![Obidome Screenshot](https://github.com/hisaknown/obidome/raw/refs/heads/main/doc/screenshot.png)

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
refresh_interval_msec: 1000  # Refresh every 1 second
margin_right: 10  # Margin from the right edge of the taskbar
sparkline_settings:  # Settings for sparkline plots
  cpu_percent:
    width: 50  # Width of the sparkline image (can be scaled in HTML)
    height: 30  # Height of the sparkline image (can be scaled in HTML)
    max_length: 30  # Number of data points to keep
    max_value: 100.0  # Maximum value for scaling (can be null for auto)
    min_value: 0.0  # Minimum value for scaling (can be null for auto)
    line_color: '#00ff00'  # Color of the sparkline line
    fill_style: gradient  # Fill style: 'solid', 'gradient', or 'none'
    fill_color: '#00ff00'  # Fill color (used if fill_style is 'solid' or 'gradient')
  ram_percent:
    width: 50
    height: 30
    max_length: 30
    max_value: 100.0
    min_value: 0.0
    line_color: '#4499ff'
    fill_style: gradient
    fill_color: '#4499ff'

custom_keys:  # Custom shell commands to display their output (key_name: command)
  gpu_temp: "nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader"

container_stylesheet: |  # CSS styles for the whole content
  font-family: 'Consolas', 'monospace';
  font-size: 14px;
  padding: 0px;
 
info_label: |  # HTML template for the info label
  <table width="100%" cellspacing="0" cellpadding="0">
      <tr>
          <td align="right" style="color: #aaaaaa; padding-right: 4px;">CPU:</td>
          <td align="left" style="color: #ffffff;">{cpu_percent:4.1f}%</td>
          <td><img src="{cpu_percent_sparkline}" width="25" height="15"></td>
      </tr>
      <tr>
          <td align="right" style="color: #aaaaaa; padding-right: 4px;">RAM:</td>
          <td align="left" style="color: #ffffff;">{ram_percent:4.1f}%</td>
          <td><img src="{ram_percent_sparkline}" width="25" height="15"></td>
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
| Key | Type | Description |
|-----|------|-------------|
|`{cpu_percent}` | float | Current CPU usage percentage. |
|-----|------|-------------|
|`{cpu_demanding_process}` | str | Name of the process using the most CPU (requires Admin). |
|`{cpu_demanding_process_cpu_percent}` | float | CPU usage of the most demanding process (requires Admin). |

#### RAM
| Key | Type | Description |
|-----|------|-------------|
|`{ram_percent}` | float | Current RAM usage percentage. |
|-----|------|-------------|
|`{ram_used}` | int | Used RAM in Bytes. |
|`{ram_used_mb}` | float | Used RAM in Megabytes. |
|`{ram_used_gb}` | float | Used RAM in Gigabytes. |
|-----|------|-------------|
|`{ram_total}` | int | Total system RAM in Bytes. |
|`{ram_total_mb}` | float | Total system RAM in Megabytes. |
|`{ram_total_gb}` | float | Total system RAM in Gigabytes. |

#### Network
| Key | Type | Description |
|-----|------|-------------|
|`{network_bytes_sent}` | int | Total bytes sent. |
|`{network_kb_sent}` | float | Total KB sent. |
|`{network_mb_sent}` | float | Total MB sent. |
|-----|------|-------------|
|`{network_bytes_sent_per_sec}` | float | Bytes sent per second. |
|`{network_kb_sent_per_sec}` | float | KB sent per second. |
|`{network_mb_sent_per_sec}` | float | MB sent per second. |
|-----|------|-------------|
|`{network_bytes_recv}` | int | Total bytes received. |
|`{network_kb_recv}` | float | Total KB received. |
|`{network_mb_recv}` | float | Total MB received. |
|`{network_gb_recv}` | float | Total GB received. |
|-----|------|-------------|
|`{network_bytes_recv_per_sec}` | float | Bytes received per second. |
|`{network_kb_recv_per_sec}` | float | KB received per second. |
|`{network_mb_recv_per_sec}` | float | MB received per second. |
|`{network_gb_recv_per_sec}` | float | GB received per second. |

#### Disk I/O
| Key | Type | Description |
|-----|------|-------------|
|`{disk_io_read_bytes}` | int | Total bytes read. |
|`{disk_io_read_kb}` | float | Total KB read. |
|`{disk_io_read_mb}` | float | Total MB read. |
|`{disk_io_read_gb}` | float | Total GB read. |
|-----|------|-------------|
|`{disk_io_read_bytes_per_sec}` | float | Bytes read per second. |
|`{disk_io_read_kb_per_sec}` | float | KB read per second. |
|`{disk_io_read_mb_per_sec}` | float | MB read per second. |
|`{disk_io_read_gb_per_sec}` | float | GB read per second. |
|-----|------|-------------|
|`{disk_io_write_bytes}` | int | Total bytes written. |
|`{disk_io_write_kb}` | float | Total KB written. |
|`{disk_io_write_mb}` | float | Total MB written. |
|`{disk_io_write_gb}` | float | Total GB written. |
|-----|------|-------------|
|`{disk_io_write_bytes_per_sec}` | float | Bytes written per second. |
|`{disk_io_write_kb_per_sec}` | float | KB written per second. |
|`{disk_io_write_mb_per_sec}` | float | MB written per second. |
|`{disk_io_write_gb_per_sec}` | float | GB written per second. |

#### Plotting
* `{<ANY_NUMERIC_KEY>_sparkline}`: Base64-encoded sparkline image for the specified key. Replace `<ANY_NUMERIC_KEY>` with any numeric metric key.
    * Example:
        * `cpu_percent` (-> `cpu_percent_sparkline`)
        * `ram_percent` (-> `ram_percent_sparkline`)
    * The type is `str` (data URL of PNG image).
    * Styles like line colors should be configured in `settings.yaml`.

#### Custom
* `{custom_key_name}`: The output of the shell command defined in `custom_keys`.

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
