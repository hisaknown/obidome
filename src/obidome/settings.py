"""Settings module for Obidome."""

from platformdirs import user_config_path
from pydantic import Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict, YamlConfigSettingsSource
from yaml import safe_dump

CONFIG_PATH = user_config_path("obidome") / "settings.yaml"


class ObidomeSettings(BaseSettings):
    """Settings for Obidome application."""

    refresh_interval_msec: int = Field(default=1000, description="Refresh interval in milliseconds")
    margin_right: int = Field(default=10, description="Right margin from the tray area in pixels")

    container_stylesheet: str = Field(
        default=("font-family: 'Consolas', 'monospace';\nfont-size: 14px;\npadding: 0px;\n"),
        description="Stylesheet for the container",
    )
    info_label: str = Field(
        default="""<table width="100%" cellspacing="0" cellpadding="0">
    <tr>
        <td align="right" style="color: #aaaaaa; padding-right: 4px;">CPU:</td>
        <td align="left" style="color: #ffffff; white-space: pre;">{cpu_percent:4.1f}<span style="font-size:9px">%</span></td>
    </tr>
    <tr>
        <td align="right" style="color: #aaaaaa; padding-right: 4px;">RAM:</td>
        <td align="left" style="color: #ffffff; white-space: pre;">{ram_percent:4.1f}<span style="font-size:9px">%</span></td>
        <td align="left"></td>
    </tr>
</table>
""",  # noqa: E501
        description="HTML template for the info label",
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
        del init_settings, env_settings, dotenv_settings, file_secret_settings  # Unused
        return (YamlConfigSettingsSource(settings_cls),)

    def save(self) -> None:
        """Save the current settings to the YAML configuration file."""
        settings = self.model_dump()
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with CONFIG_PATH.open("w", encoding="utf-8") as f:
            safe_dump(settings, f)
