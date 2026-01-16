"""Settings module for Obidome."""

from typing import Literal

import yaml
from platformdirs import user_config_path
from pydantic import Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict, YamlConfigSettingsSource

CONFIG_PATH = user_config_path("obidome") / "settings.yaml"


def str_presenter(dumper: yaml.Dumper, data: str) -> yaml.nodes.ScalarNode:
    """Set YAML string representation to literal style for multiline strings."""
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


yaml.add_representer(str, str_presenter)


class SparklineSettings(BaseSettings):
    """Settings for sparkline plots."""

    line_color: str = Field(default="#00ff00", description="Color of the sparkline line")
    fill_style: Literal["solid", "gradient", "none"] = Field(
        default="gradient", description="Fill style of the sparkline"
    )
    fill_color: str = Field(
        default="#00ff00", description="Fill color of the sparkline when fill style is solid or gradient"
    )


class ObidomeSettings(BaseSettings):
    """Settings for Obidome application."""

    refresh_interval_msec: int = Field(default=1000, description="Refresh interval in milliseconds")
    margin_right: int = Field(default=10, description="Right margin from the tray area in pixels")

    cpu_percent_plot_settings: SparklineSettings = Field(
        default=SparklineSettings(
            line_color="#00ff00",
            fill_style="gradient",
            fill_color="#00ff00",
        ),
        description="Settings for the CPU usage sparkline plot",
    )

    ram_percent_plot_settings: SparklineSettings = Field(
        default=SparklineSettings(
            line_color="#4499ff",
            fill_style="gradient",
            fill_color="#4499ff",
        ),
        description="Settings for the RAM usage sparkline plot",
    )

    container_stylesheet: str = Field(
        default=("font-family: 'Consolas', 'monospace';\nfont-size: 14px;\npadding: 0px;\n"),
        description="Stylesheet for the container. Can be multiline.",
    )
    info_label: str = Field(
        default="""<table width="100%" cellspacing="0" cellpadding="0">
    <tr style="background-image: url({cpu_percent_plot}); background-size: contain;">
        <td align="right" style="color: #aaaaaa; padding-right: 4px;">CPU:</td>
        <td align="left" style="color: #ffffff; white-space: pre;">{cpu_percent:4.1f}<span style="font-size:9px">%</span></td>
        <td><img src="{cpu_percent_plot}" width="25" height="15"></td>
    </tr>
    <tr>
        <td align="right" style="color: #aaaaaa; padding-right: 4px;">RAM:</td>
        <td align="left" style="color: #ffffff; white-space: pre;">{ram_percent:4.1f}<span style="font-size:9px">%</span></td>
        <td><img src="{ram_percent_plot}" width="25" height="15"></td>
        <td align="left"></td>
    </tr>
</table>
""",  # noqa: E501
        description="HTML template for the info label. Can be multiline.",
    )

    model_config = SettingsConfigDict(yaml_file=CONFIG_PATH)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Customize the settings sources to use YAML file."""
        del env_settings, dotenv_settings, file_secret_settings  # Unused
        return (init_settings, YamlConfigSettingsSource(settings_cls))

    def save(self) -> None:
        """Save the current settings to the YAML configuration file."""
        settings = self.model_dump()
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with CONFIG_PATH.open("w", encoding="utf-8") as f:
            yaml.dump(settings, f, default_flow_style=False, allow_unicode=True)
