#!/usr/bin/env python
#-*- coding: utf-8 -*-
#
# Copyright (C) 2009 Maxim Kovalev
#
# This file is part of NyaaFS
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# $Id: systables.py 25 2009-05-30 08:44:31Z Maxim.Kovalev $


class systables(object):
    def __init__(self, cursor, base):
        self.db = base
        self.cu = cursor
        self.cu.execute("""SELECT name FROM sqlite_master WHERE \
name = 'sys_file_id'""")
        result = self.cu.fetchall()
        #FIXME какая то фигня, он все равно пытается создать таблицу
        if len(result) ==0:
            self.cu.execute("""CREATE TABLE sys_file_id(\
id INTEGER NOT NULL PRIMARY KEY,\
name TEXT NOT NULL)""")
            self.db.commit()
        self.cu.execute("""SELECT name FROM sqlite_master WHERE \
name = 'sys_hw_names'""")
        result = self.cu.fetchall()
        if len(result) == 0:
            self.cu.execute("""CREATE TABLE sys_hw_names(\
id INTEGER PRIMARY KEY,\
name TEXT NOT NULL)""")
        self.db.commit()
        
    def drop(self):
        self.cu.execute("""DROP TABLE sys_file_id""")
        self.cu.execute("""DROP TABLE sys_hw_names""")
        self.db.commit()
        
    def add_file(self, name):
        self.cu.execute("SELECT id FROM sys_file_id\
 WHERE name = '%s'" % name)
        old_state = self.cu.fetchall()
        self.cu.execute("INSERT INTO sys_file_id (name) VALUES ('%s')"\
% name)
        self.db.commit()
        self.cu.execute("SELECT id FROM sys_file_id\
 WHERE name = '%s'" % name)
        new_state = self.cu.fetchall()
        for item in new_state:
            if item in old_state:
                continue
            else:
                new_id = item[0]
                break
        self.cu.execute("INSERT INTO sys_hw_names (id, name) VALUES\
(%d, '%s')" % (new_id, str(new_id) ))
        self.db.commit()
        return new_id
    
    def del_file(self, id):
        self.cu.execute("DELETE FROM sys_file_id WHERE id = %d" % id)
        self.cu.execute("DELETE FROM sys_hw_names WHERE id = %d" % id)
        self.db.commit()
        
    def rename_file(self, id, new_name):
        self.cu.execute("UPDATE sys_file_id SET name = '%s'\
 WHERE id = %d" % (new_name, id))
        self.db.commit()
