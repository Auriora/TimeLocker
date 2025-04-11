"""Configuration classes for PlantUML diagram generation."""

import os
from typing import Dict, List, Optional
from os.path import abspath

class PlantUMLConfig:
    """Configuration for PlantUML server and diagram settings."""
    def __init__(self, 
                 server_url: str = 'http://www.plantuml.com/plantuml/svg/',
                 basic_auth: Optional[dict] = None,
                 form_auth: Optional[dict] = None,
                 http_opts: Optional[dict] = None,
                 request_opts: Optional[dict] = None):
        self.server_url = server_url
        self.basic_auth = basic_auth or {}
        self.form_auth = form_auth or {}
        self.http_opts = http_opts or {}
        self.request_opts = request_opts or {}

class ProjectConfig:
    """Configuration for project paths and settings."""
    def __init__(self,
                 src_dir: str,
                 output_dir: str,
                 excluded_dirs: Optional[List[str]] = None,
                 package_base_name: Optional[str] = None):
        self.src_dir = abspath(src_dir)
        self.output_dir = abspath(output_dir)
        self.excluded_dirs = excluded_dirs or []
        self.package_base_name = package_base_name

    def ensure_output_dir(self) -> None:
        """Ensure output directory exists."""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)