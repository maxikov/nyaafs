#!/usr/bin/env python
#-*- coding: utf-8 -*-
#
# Copyright (C) 2009 Maxim Kovalev, Vladimir Badaev
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
# $Id: hierarchy.py 94 2009-06-06 19:33:09Z Maxim.Kovalev $

"""
Иерархия является обобщением понятия дерева директорий. Пользователь
может сам создавать свои иерархии, тогда как иерархия с именем default
существует всегда и отвечает за обычное дерево директорий.
"""

import unix_attr
import time
import errno
from nyaerror import NyaError

class hierarchy(object):
    """
    Единсственный класс отвечает сразу за всю иерархию, подробнее смотри в описании модуля.
    """
    def __init__(self, name, cursor, base):
        """
        Конструктор принимает имя иерархии, курсор базы данных и её объект-соединение.
        Если находит в базе иерархию с переданным именем, то подключается к ней, если же нет --- создаёт новую.
        """
        #FIXME --- да, чуть не забыл. Создание иерарзии требует, чтобы в базе существовала таблица sys_file_id,
        # в которой хранится связь между ID файлов и их именами. Надо бы этот факт проверять, 
        # а в случае отсутствия выкидывать исключение.

        self.cu = cursor
        self.name = name
        self.db = base
        self.cu.execute("SELECT name FROM sqlite_master WHERE name LIKE 'hierarchy_%s_%%'" % self.name)
        #FIXME Ёбаный стыд, сраный SQLite не поддерживает сраные схемы. Это печально.
        # Придётся делать руками быдлопространства имён с помощью подчёркиваний.
        #FIXME Вообще-то, в SQL-запросах LIKE символ _ означает любой (один) символ.
        # Как escape-последовательности делаются в SQLite, я не понял. Эх, надо было Postgres брать...
        result = self.cu.fetchall()
        if len(result) != 4:
            #FIXME --- Вообще-то возможны три варианта: либо нужных таблиц вообще нет, либо их правильное количество
            # (я думал, что три, но забыл про атрибуты для директорий, возможно на самом деле должно быть четыре),
            # либо их какое-то другое число. В первом случае такие таблицы создаются, во втором ничего не происходит,
            # а вот для третьего надо сочинить исключение.
            try:
                self.cu.execute("CREATE TABLE hierarchy_%s_dir_id (\
id INTEGER NOT NULL,\
name TEXT,\
PRIMARY KEY(id),\
FOREIGN KEY (id)\
REFERENCES hierarchy_%s_dir_hierarchy (id))"\
                    % (self.name, self.name))
                self.cu.execute("CREATE TABLE hierarchy_%s_dir_hierarchy (\
id INTEGER NOT NULL,\
parent INTEGER NOT NULL,\
PRIMARY KEY(id),\
FOREIGN KEY(parent)\
REFERENCES hierarchy_%s_dir_hierarchy (id),\
FOREIGN KEY(id)\
REFERENCES hierarchy_%s_dir_id (id))" % (self.name, self.name, self.name))
                self.cu.execute("CREATE TABLE hierarchy_%s_file_parents(\
file_id INTEGER NOT NULL,\
parent INTEGER NOT NULL,\
PRIMARY KEY(file_id),\
FOREIGN KEY(parent)\
REFERENCES hierarchy_%s_dir_id(id))"\
                    % (self.name, self.name))
                self.cu.execute("""INSERT INTO hierarchy_%s_dir_id VALUES (0, 'root')""" % self.name)
                self.dir_attrs = unix_attr.unix_attr("hierarchy_%s" %\
                                                     self.name,\
                                                     self.cu,\
                                                     self.db)
                tmp = int(time.time())
                self.dir_attrs.add_item(0, {"st_atime": tmp, "st_ctime": tmp, "st_mtime": tmp}) #FIXME --- кто-нибудь знает атрибуты корневой директории?
            #FIXME --- для всей этой херни надо добавить исключения на случай, если хоть что-нибудь из этой цепочки не удастся сделать.
            except NyaError, e:
                raise e
            except Exception, e:
                # FIXME: ОМГ... поидее тут должно быть sqlite3.Error(ну или там db.Error) где брать модуль склайта,
                # я не знаю, поэтому буду ловить все.
                raise NyaError("Can't add hierarchy %s to db. Error: %s" % (self.name, e.message), self.__class__, "__init__")
            self.db.commit()
            #По-моему, SQLite автоматом коммитит вообще все транзакции. Это херня какая-то,
            # так что на всякий случай пишу руками везде, где это действительно нужно.
            # Лишним не будет, а не исключено, что автоматический коммит можно отключить, 
            # это понадобится для создания нормальной журналиромоей FS

    def find_by_path_OLD(self, path):
        """
        Поиск ID файла или директории по указанному абсолютному пути.
        Принимает список строк, первой обязательно должна быть "root", остальные --- элементы пути.
        Возвращает кортеж из ID, строки с именем (ну и нафига я это сделал, скажите пожалуйста?)
        и строки "dir" или "file" в зависимости от того, что является послежним элементом пути (собственно искомым файлом)
        """
        #FIXME --- добавить исключение на случай, если первым элементом пути НЕ является строка "root"
        if path[0] != 'root': 
            # Надеюсь я правильно тебя понял, Макс.
            #Угу...
            raise NyaError("First element of path is not 'root'", self.__class__, "find_by_path") 

        def file_or_dir(self, dir_id, name):
            """
            Поиск файла или директории с указанным именем.
            Принимает ID директории, в которой ищем, и имя файла или директории, котор(ый|ую) ищем.
            Возвращает кортеж из строки "file" или "dir" в зависимости от того, что нашли 
            (условие: в одной директории не может существовать файла и директории с одинаковыми именами), и ID
            """

            #FIXME -- Вот здесь надо как-то (я ещё не придумал, как) сделать исключение для случая,
            # когда искомого файла вообще не существует. То есть, проверяем, есть ли директория с таким именем, 
            # если нет --- есть ли файл с таким именем, а если вообще нифига нет, то надо бы исключение выкинуть
            self.cu.execute("SELECT I.id FROM hierarchy_%s_dir_id I, hierarchy_%s_dir_hierarchy H\
 WHERE H.parent = %d AND I.name = '%s' AND I.id = H.id" % (self.name, self.name, dir_id, name))
            result = self.cu.fetchall()
            if self.cu.rowcount == 1:
                return ("dir", result[0][0])
            self.cu.execute("SELECT SF.id FROM sys_file_id SF, hierarchy_%s_file_parents FP\
 WHERE FP.parent = %d AND SF.name = '%s' AND FP.file_id = SF.id" % (self.name, dir_id, name))
            result = self.cu.fetchall()

            if len(result) == 0:
                raise NyaError("No such file or directory: %s" % name, self.__class__, "find_by_path.file_or_dir", fatal=False, errno=errno.ENOENT)
            return ("file", result[0][0])

        def add_to_request(self, request, path):
            """
            Сугубо служебная функция, нужная для формаирования подчинённого SQL-запроса по переаднному пути.
            Будучи рекурсивной, принимает баазовый запрос, который должен давать ID директории,
            в которой будем искать слудующую, и путь. Возвращает запрос, который ищет 
            следующий элемент пути в найденной директории.
            """
            if (len(path) <= 2):
                return request
            else:
                return ("SELECT DIH.id FROM hierarchy_%s_dir_id DID, hierarchy_%s_dir_hierarchy DIH\
 WHERE DID.name = '%s' AND DIH.parent = (%s) AND DID.id = DIH.id"\
                    % (self.name, self.name, path[-1], add_to_request(self, request, path[:-1])))

        if len(path) == 1:
            #Если путь длины 1 - то это просто строка "root" (это нам гарантирует исключение, 
            # которое должно быть вставлено выше), а значит смело возвращем ID 0
            # (см. на конструктор --- корневая директория всегда имеет ID 0)
            return "dir", 0
        elif len(path) == 2:
            #Если в пути два элемента, то мы точно знаем, что второй является файлом или  директорией, лежащей в корневой.
            return file_or_dir(self, 0, path[-1])

        else:
            #Понеслась моча по трубам...
            request = ("SELECT DIH.id FROM hierarchy_%s_dir_id DID, hierarchy_%s_dir_hierarchy\
 DIH WHERE DIH.parent = 0 AND DID.name = '%s' AND DID.id = DIH.id" % (self.name, self.name, path[1]))
            request = add_to_request(self, request, path[:-1])
            self.cu.execute(request)
            result = self.cu.fetchall()
            #FIXME -- Надо добавить исключение на случай некорректного пути.
            # Это как минимум. Как максимум --- два исключения.
            #  Первое ловит отсуствие той или иной директории в пути.
            #  Второе ловит случай того, что файл является не последним элементом пути.
            # Ниасилил. 
            cwdid = result[0][0]
            return file_or_dir(self, cwdid, path[-1])

    def add_dir_to_dir(self, parent, name):
        """
        Создание директории с указанным именем в указанной директории.
        Принимает ID родительской директории и имя директории, которую хотим создать.
        Ничего не возвращет (хотя, можно потом чисто по приколу сделать её возвращающей ID созданной директории,
        благо мы и так его ищем).
        """
        print "hierarchy.add_dir_to_dir(%s,%s)" % (parent, name)
        #FIXME -- Здесь нужно целых три исключения.
        # Что если не существует директории с переданным в качестве родительского ID?
        # raise NyaError("Bad parent directory ID = %s" % ID, self.__class__, "add_dir_to_dir")
        # Что если такая директория уже существует?
        # raise NyaError("Can't create dir %s: File exists" % NAME, self.__class__, "add_dir_to_dir")
        # Что если такой файл уже существует?
        # raise NyaError("Can't create dir %s: File exists" % NAME, self.__class__, "add_dir_to_dir")
        self.cu.execute("SELECT DID.id FROM hierarchy_%s_dir_id DID WHERE DID.name = '%s'" % (self.name, name))
        old_state = self.cu.fetchall()
        self.cu.execute("INSERT INTO hierarchy_%s_dir_id (name) \
VALUES ('%s')""" % (self.name, name))
        self.cu.execute("SELECT id FROM hierarchy_%s_dir_id \
WHERE name = '%s'" % (self.name, name))
        new_state = self.cu.fetchall()
        for item in new_state:
            if item in old_state:
                continue
            else:
                added = item[0]
                break
        self.cu.execute("INSERT INTO hierarchy_%s_dir_hierarchy (id, parent) \
VALUES (%d, %d)" % (self.name, added, parent))
        self.db.commit()
        return added
    
    def read_dir(self, dir_id):
        """
        Читает список файлов и поддиректорий в данной директории.
        Принимает ID нужной директории.
        Возвращает список кортежей из ID, имени и строки "file" или "dir" в зависимости от типа элемента.
        На будущее неплохо бы прикрутить сортировку результата.
        """
        print "hierarchy.read_dir(%s)" % dir_id
        #FIXED --- Исключение на случай, если указанной директории не существует.
        self.cu.execute("SELECT * FROM hierarchy_%s_dir_id WHERE id = %d" % (self.name, dir_id))
        dirs = self.cu.fetchall()

        #print "hierarchy.read_dir() dirs = %s" % dirs
        
        if len(dirs) == 0:
            #NAME or dir_id -- в этой функции мы имеем только id директории.
            # Если не может её найти -- то и никакого имени нет.
            raise NyaError("No such directory: DID%s" % dir_id, self.__class__, "read_dir", fatal=False, errno=errno.ENOENT)
        self.cu.execute("SELECT DID.id, DID.name FROM hierarchy_%s_dir_id DID, hierarchy_%s_dir_hierarchy DIH WHERE DID.id = DIH.id AND DIH.parent = %d" % (self.name, self.name, dir_id))
        dirs = self.cu.fetchall()

        #print "hierarchy.read_dir() dirs = %s" % dirs



        #for i in xrange(len(dirs)):
        #    id, name = dirs[i]
        #    dirs[i] = (id, name, "dir")
            #Ядрёна мать, я только сейчас понял, что я здесь сделал: я беру и меняю типы элементов списка,
            # не разрущая сам список. О нет, я безнадёжно подсел на иглу динамической типизации, сам того не заметив ;_;
            #
        dirs = map((lambda (id, name): (id, name, "dir")), dirs)
        self.cu.execute("SELECT SF.id, SF.name FROM hierarchy_%s_file_parents FP, sys_file_id SF WHERE SF.id = FP.file_id AND FP.parent = %d" % (self.name, dir_id))
        files = self.cu.fetchall()
        
        #for i in xrange(len(files)):
        #    id, name  = files[i]
        #    files[i] = (id, name, "file")
        files = map((lambda (id, name): (id, name, "file")), files)
        #  или хотя бы
        #  for i in files:
        #   id, name = i
        #   i = (id, name, "file")

        print "hierarchy.read_dir() dirs = %s, files = %s" % (dirs, files)
        points = [(dir_id, '.', "dir"), (0, '..', "dir")]
        return (dirs + files + points)
    
    def del_dir(self, id):
        #FIXED --- стандартно: проверить существоание директории
        list =  self.read_dir(id)
        list = map( (lambda (i, n, t) :n), list)
        if list!= ['.', '..'] and list!= ['..', '.'] and list != []:
            #Исключение на случай непустой директории
            raise NyaError("Directorry is not empty: %s" % id, self.__class__, "del_dir")
        self.cu.execute("DELETE FROM hierarchy_%s_dir_id \
WHERE id = %d" % (self.name, id))
        self.cu.execute("DELETE FROM hierarchy_%s_dir_hierarchy \
WHERE id = %d" % (self.name, id))
        self.db.commit()
#        self.dir_attrs.delele_item(id)
        
    def find_by_path(self, path):
        cwd = 0
        if len(path)==1:
            return ('dir', 0)
        elif len(path)==2:
            for entry in self.read_dir(0):
                if entry[1]==path[1]:                    return (entry[2], entry[0])
            raise NyaError("No such file or directory: %s" % path[-1], self.__class__, "find_by_path", fatal=False, errno=errno.ENOENT)

#            raise NyaError("No such file or directory: %s" % path, self.__class__, "find_by_path.file_or_dir", fatal=False, errno=errno.ENOENT)

        else:
            last = path[-1]
            path = path[1:-1]
            print "find_by_paht last = ", last
            print "find_by_paht path = ", path
            for item in path:
                print "find_by_path() item = ", item
                for entry in self.read_dir(cwd):
#                    if entry[1]==item and entry[2]=="dir":
 #                       cwd = entry[0]
  #                      print "find_by_path() cwd = ", cwd
   #                     break
    #                for entry in self.read_dir(cwd):
     #                   if entry[1]==last:
      #                      return (entry[2], entry[0])
                    if entry[1]==item:
                        if entry[2] == "dir":
                            cwd = entry[0]
                            print "find_by_path() cwd = ", cwd
                        else:
                            raise NyaError("This is file, stupid!: %s" % path[-1], self.__class__, "find_by_path", fatal=False, errno=errno.ENOENT)
                for entry in self.read_dir(cwd):
                    if entry[1]==last:
                        return (entry[2], entry[0])

            
            raise NyaError("No such file or directory: %s" % path[-1], self.__class__, "find_by_path", fatal=False, errno=errno.ENOENT)

    def drop(self):
        del self.dir_attrs
        # V.B   ОМГ, Макс, зачем сносить таблицу при удалении объекта? Мы ж в ней все дерево храним.
        #       При отмонтировании оно все похерится.
        self.cu.execute("DROP TABLE hierarchy_%s_dir_id" % self.name)
        self.cu.execute("DROP TABLE hierarchy_%s_dir_hierarchy" % self.name)
        self.cu.execute("DROP TABLE hierarchy_%s_file_parents" % self.name)
        self.db.commit()
        
    def del_file_from_dir(self, dir_id, file_id):
        #FIXME --- если файла не существует или нет директории
        #  raise NyaError("No such file or directory: %s" % file_id, self.__class__, "del_file_from_dir")
        self.cu.execute("DELETE FROM hierarchy_%s_file_parents \
WHERE file_id = %d AND parent = %d" % (self.name, file_id, dir_id))
        self.db.commit()
        
    def add_file_to_dir(self, dir_id, file_id):
        self.cu.execute("SELECT * FROM hierarchy_%s_file_parents \
WHERE file_id = %d AND parent = %d" % (self.name, file_id, dir_id))
        result = self.cu.fetchall()
        if len(result) != 0:
            pass #ERROR
        self.cu.execute("INSERT INTO hierarchy_%s_file_parents \
(file_id, parent) VALUES (%d, %d)" % (self.name, file_id, dir_id))
        self.db.commit()
#FIXME --- Этот модуль выглядит так, будто ему чего-то не хватает...
    def move_dir(self, dir_id, new_parent):
        self.cu.execute("UPDATE hierarchy_%s_dir_hierarchy\
        SET parent = %d WHERE id = %d" %\
        (self.name, new_parent, dir_id))
        self.db.commit()
        
    def move_file(self, file_id, new_parent):
        self.cu.execute("UPDATE hierarchy_%s_file_parents\
        SET parent = %d WHERE file_id = %d" %\
        (self.name, new_parent, file_id))
        self.db.commit()
        
    def rename_dir(self, dir_id, new_name):
        self.cu.execute("UPDATE hierarchy_%s_dir_id\
        SET name = '%s' WHERE id = %d"%\
        (self.name, new_name, dir_id))
        self.db.commit()
        