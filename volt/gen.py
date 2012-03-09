# -*- coding: utf-8 -*-
"""
--------
volt.gen
--------

Volt site generator.

:copyright: (c) 2012 Wibowo Arindrarto <bow@bow.web.id>
:license: BSD

"""


import os
import shutil

from volt import util
from volt.config import CONFIG, SessionConfig
from volt.config.base import path_import
from volt.engines import Engine
from volt.plugins import Plugin
from volt.util import grab_class


class Generator(object):

    """Class representing a Volt run."""

    def get_processor_mod(self, processor_name, processor_type, \
            volt_dir=os.path.dirname(__file__), user_dir=None):
        """Returns the engine or plugin class used in site generation.

        Args:
            processor_name - String denoting engine or plugin name.
            processor_type - String denoting processor type. Must be 'engines'
                or 'plugins'.
            volt_dir - String denoting absolute path to Volt's installation
                directory.
            user_dir - String denoting absolute path to user's Volt project
                directory.
        
        This method tries to load engines or plugins from the user's Volt
        project directory first. Failing that, it will try to import engines
        or plugins from Volt's installation directory.

        """
        # check first if processor type is 'plugins' or 'engines'
        assert processor_type in ['engines', 'plugins'], \
            "Processor type must be 'engines' or 'plugins'"

        # because if we set user_dir default value in arglist
        # it's harder to test
        if not user_dir:
            user_dir = CONFIG.VOLT.ROOT_DIR

        # load engine or plugin
        # user_path has priority over volt_path
        user_path = os.path.join(user_dir, processor_type)
        volt_path = os.path.join(volt_dir, processor_type)

        return path_import(processor_name, [user_path, volt_path])


    def activate(self):
        """Runs all the engines and plugins according to the configurations.

        This method consists of four distinct steps that results in the final
        site generation:

            1. Engine activation: all engines listed in CONFIG.SITE.ENGINES are
               loaded. Any engines found in the user directory takes
               precedence over built-in engines. The engines' activate() method
               are then run. This usually means the engines' units are parsed
               and stored as its instance attributes in self.units.

            2. Plugin run: plugins listed in CONFIG.SITE.PLUGINS are loaded and
               run against their target engines.

            3. Engine dispatch: after the engine units have been processed by
               the plugins, the engines are then dispatched. This will involve
               writing the actual HTML files for each engine. Pack-building, if
               defined for an engine, should be run in this step prior to
               writing.

            4. Non-engine template processing: site pages that do not belong to
               any engines are then processed. Examples of pages in this
               category are the main index.html and the 404 page. If any engine
               has defined a main index.html, this method will not write
               another index.html.

        """
        self.engines = dict()

        # activate engines
        for engine in CONFIG.SITE.ENGINES:
            engine_mod = self.get_processor_mod(engine, 'engines')
            engine_class = grab_class(engine_mod, Engine)
            self.engines[engine] = engine_class()

            util.show_notif("  => ", is_bright=True)
            util.show_info("%s engine activated\n" % engine.capitalize())
            self.engines[engine].activate()

        # run plugins
        for plugin, target_engine in CONFIG.SITE.PLUGINS:
            plugin_mod = self.get_processor_mod(plugin, 'plugins')
            plugin_class = grab_class(plugin_mod, Plugin)

            if plugin_class:
                # set default args in CONFIG first before instantiating
                CONFIG.set_plugin_defaults(plugin_class.DEFAULT_ARGS)
                plugin_obj = plugin_class()

                for engine in target_engine:
                    util.show_warning("  => ", is_bright=True)
                    util.show_info("%s plugin activated -- running on %s units\n" % \
                            (plugin.capitalize(), engine.capitalize()))
                    plugin_obj.run(self.engines[engine].units)

        # dispatch engines
        for engine in self.engines.values():
            engine.dispatch()

        # generate other pages
        tpl_file = 'index.html'
        template = CONFIG.SITE.TEMPLATE_ENV.get_template(tpl_file)

        outfile = os.path.join(CONFIG.VOLT.SITE_DIR, 'index.html')
        if not os.path.exists(outfile):
            with open(outfile, 'w') as target:
                target.write(template.render(page={}, CONFIG=CONFIG))


def run():
    """Generates the site."""

    # reload config to reflect any new changes that may have been made
    CONFIG = SessionConfig()

    # prepare output directory
    if os.path.exists(CONFIG.VOLT.SITE_DIR):
        shutil.rmtree(CONFIG.VOLT.SITE_DIR)
    shutil.copytree(CONFIG.VOLT.LAYOUT_DIR, CONFIG.VOLT.SITE_DIR, \
            ignore=shutil.ignore_patterns(CONFIG.VOLT.IGNORE_PATTERN))

    util.show_info("Volt site generation start!\n", is_bright=True)

    # generate the site!
    Generator().activate()

    util.show_info("Site generation finished.\n", is_bright=True)
