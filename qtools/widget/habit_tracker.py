# Copyright (c) 2020 Matt Colligan
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import json
import os
from datetime import datetime, timedelta

from libqtile import bar
from libqtile.log_utils import logger
from libqtile.utils import get_cache_dir
from libqtile.widget import base


_CACHE = os.path.join(get_cache_dir(), 'habit_tracker_count.json')


class HabitTracker(base._Widget):
    """
    A don't-break-the-chain style habit tracker widget.

    The current chain lengths are stored in a JSON file containing a dictionary where
    each key is the name of a habit. This habit can be passed to the widget to identify
    a chain.

    The chain can be drawn in different styles:

        - "chain": A simple chain of connected squares that grows through the grid as it
          increases in length.
        - "base": A grid of squares where each column represents one digit in a counting
          scheme using the base (rows + 1). For example, HabitTracker(rows=1) would draw
          a single row of squares that are filled in to represent a binary count.

    """
    defaults = [
        ("colour", "1667EB", "Fill colour."),
        ("chain_file", _CACHE, "File that stores the chain lengths."),
        ("habit", "anon", "Habit name. Used for identifying the chain in the cache file."),
        ("margin_x", 4, "X margin."),
        ("margin_y", 4, "Y margin."),
        ("style", "chain", "Counter style, one of: chain, base"),
        ("rows", 2, "Number of rows."),
        ("columns", 4, "Number of columns."),
        ("blank_colour", None, "Colour for placeholder blocks."),
    ]

    def __init__(self, **config):
        base._Widget.__init__(self, bar.CALCULATED, **config)
        self.add_defaults(HabitTracker.defaults)
        self._chain = None
        self._block_size = 0

        self._load_chain()

        if not hasattr(self, "draw_{0}".format(self.style)):
            logger.warning("HabitTracker style '{0}' invalid.".format(self.style))
            self.style = "chain"

        if 'Button1' not in self.mouse_callbacks:
            self.mouse_callbacks.update({'Button1': self.cmd_increment})
        if 'Button2' not in self.mouse_callbacks:
            self.mouse_callbacks.update({'Button2': self.cmd_reset})
        if 'Button3' not in self.mouse_callbacks:
            self.mouse_callbacks.update({'Button3': self.cmd_decrement})

    def _load_chain(self):
        if os.path.isfile(self.chain_file):
            with open(self.chain_file, 'r') as fd:
                cache = json.load(fd)
            if self.habit in cache.keys():
                start_date = datetime.strptime(cache.get(self.habit), "%Y-%m-%d")
                self._chain = (datetime.now() - start_date).days
                return
        self._chain = 0
        self._save_chain()

    def _save_chain(self):
        cache = {}
        if os.path.isfile(self.chain_file):
            with open(self.chain_file, 'r') as fd:
                cache.update(json.load(fd))
        start_date = datetime.now() - timedelta(days=self._chain)
        cache.update({self.habit: start_date.strftime("%Y-%m-%d")})
        with open(self.chain_file, 'w') as fd:
            json.dump(cache, fd)

    def cmd_increment(self, qtile=None):
        self._chain += 1
        self._save_chain()
        self.draw()

    def cmd_decrement(self, qtile=None):
        if self._chain > 0:
            self._chain -= 1
            self._save_chain()
            self.draw()

    def cmd_reset(self, qtile=None):
        self._chain = 0
        self._save_chain()
        self.draw()

    def calculate_length(self):
        space = self.bar.height - self.margin_y * 2
        self._block_size = space // (2 * self.rows - 1)
        length = self._block_size * (2 * self.columns - 1)
        return length + self.margin_x * 2

    def draw(self):
        self.drawer.clear(self.background or self.bar.background)
        getattr(self, "draw_{0}".format(self.style))()

    def draw_chain(self):
        block_size = self._block_size
        start_y = self.bar.height - self.margin_y - block_size

        if self.blank_colour:
            self.drawer.set_source_rgb(self.blank_colour)
            for col in range(self.columns):
                x_pos = self.margin_x + col * 2 * block_size
                for row in range(self.rows):
                    y_pos = start_y - row * 2 * block_size
                    self.drawer.ctx.rectangle(x_pos, y_pos, block_size, block_size)
            self.drawer.ctx.fill()

        self.drawer.set_source_rgb(self.colour)
        chain = self._chain
        for col in range(chain // self.rows + 1):
            x_pos = self.margin_x + col * 2 * block_size
            this_col = min(chain - col * self.rows, self.rows)
            rows = range(this_col)
            if col % 2:
                rows = [self.rows - 1 - i for i in rows]
            for row in rows:
                chain % ((col + 1) * self.rows)
                y_pos = start_y - row * 2 * block_size
                self.drawer.ctx.rectangle(x_pos, y_pos, block_size, block_size)

        self.drawer.ctx.fill()
        self.drawer.draw(offsetx=self.offset, width=self.length)

    def draw_base(self):
        block_size = self._block_size
        start_y = self.bar.height - self.margin_y - block_size

        if self.blank_colour:
            self.drawer.set_source_rgb(self.blank_colour)
            for col in range(self.columns):
                x_pos = self.margin_x + col * 2 * block_size
                for row in range(self.rows):
                    y_pos = start_y - row * 2 * block_size
                    self.drawer.ctx.rectangle(x_pos, y_pos, block_size, block_size)
            self.drawer.ctx.fill()

        self.drawer.set_source_rgb(self.colour)
        chain = self._chain
        for col in reversed(range(self.columns)):
            units, chain = divmod(chain, (self.rows + 1) ** col)
            if units:
                x_pos = self.margin_x + col * 2 * block_size
                for row in range(units):
                    y_pos = start_y - row * 2 * block_size
                    self.drawer.ctx.rectangle(x_pos, y_pos, block_size, block_size)

        self.drawer.ctx.fill()
        self.drawer.draw(offsetx=self.offset, width=self.length)
