#!/usr/bin/env python
"""Компонент серверной части GeoMap."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / '.env')


def main():
    """Выполняет операцию серверного компонента GeoMap."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geomap_api.settings')
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
