# -*- coding: utf-8 -*-
import pandas as pd
from typing import Literal, Tuple, Any
import csv
import os
import json
from zipfile import ZipFile
import logging
logger = logging.getLogger('root')


class parse:
    def __init__(self, args):
        self.args = args
        logger.info(
            f"typo de argumento: {type(self.args)}, valores: {self.args}")

    def execute(self) -> Literal[True]:
        JSONGroupNameAUX = ''
        xd = self.cargarPlanillaConDatosDelModelo()
        # jsonData, jsonFileName = self.readJsonData(self.args.path_to_file, self.args.nozip)
        for row in list(xd[xd["JSONGroup"].notnull()].groupby(["JSONGroup", "Table"])):
            JSONGroupName = row[0][0]
            if JSONGroupName != JSONGroupNameAUX:
                jsonData, jsonFileName = self.readJsonDataFC(JSONGroupName)

            elem = {
                "JSONGroupName": JSONGroupName,
                "TableName": row[0][1],
                "ColumnList": list(row[1]["Column"]),
                "DataType": list(row[1]["Data Type"]),
                "SIERequired": list(row[1]["SIERequired"])
            }

            _t = f'Procesando Grupo:{JSONGroupName}>Tabla:{row[0][1]}'
            logger.info(_t)
            records = self.leerTodosLosRegistrosDeLaTablaDesdeArchivoJson(jsonData, elem)

            if(records):
                self.crearCSV(jsonFileName, self.args.path_to_dir_csv_file+elem['TableName']+'.csv',
                              elem['TableName'],
                              elem['ColumnList'],
                              records)

            JSONGroupNameAUX = JSONGroupName

        _t = 'Archivo JSON completamente transformado.'
        logger.info(_t)
        return True

    # Carga planilla con todas las tablas y campos del modelo https://ceds.ed.gov
    def cargarPlanillaConDatosDelModelo(self) -> pd.DataFrame:
        #idFile = '1gBhiRXswoCN6Ub2PHtyr5cb6w9VMQgll'
        #url = f'http://drive.google.com/uc?export=download&id={idFile}'
        url = './ede/ede/NDS-Reference-v7_1.xlsx'
        xd = pd.read_excel(url, 'NDS Columns')
        _t = f'Planilla {url} cargada satisfactoriamente'
        logger.info(_t)
        return xd
    
    def readJsonDataFC(self, JSONGroupName):
        file = f"{JSONGroupName}.json"
        with open(f"{self.args.path_to_file}/{file}", mode='r', encoding="utf-8") as jsonfile:
            jsonData = json.load(jsonfile)
            _t = f"Archivo '{jsonfile}' leído sin inconvenientes\n"
            logger.info(_t)
            jsonfile.close()
        
        return jsonData, file

    # REEMPLAZADO POR readJsonDataFC
    def readJsonData(self, path_to_file: str, nozip: bool, ) -> Tuple[Any, str]:
        # Descomprime el contenido del archivo ZIP y lo carga en memoria
        if(path_to_file):
            if(not nozip):
                with ZipFile(path_to_file, 'r') as zip_ref:
                    zip_ref.extractall('./')
                    _t = f'Archivo ZIP "{path_to_file}" descomprimido con éxito'
                    logger.info(_t)
                    for file in zip_ref.namelist():
                        _t = f"Trabajando sobre archivo: '{file}'"
                        logger.info(_t)
                        with open(file, mode='r', encoding="utf-8") as jsonfile:
                            jsonData = json.load(jsonfile)
                            _t = f"Archivo '{jsonfile}' leído sin inconvenientes\n"
                            logger.info(_t)
                            jsonfile.close()
                        os.remove(file)
            else:
                file = path_to_file
                _t = f"Trabajando sobre archivo: '{file}'"
                logger.info(_t)
                with open(file, mode='r', encoding="utf-8") as jsonfile:
                    jsonData = json.load(jsonfile)
                    _t = f"Archivo '{jsonfile}' leído sin inconvenientes\n"
                    logger.info(_t)
                    jsonfile.close()

        return jsonData, file

    def leerTodosLosRegistrosDeLaTablaDesdeArchivoJson(self, jsonData: Any, elem: Any):
        try:
            # Mapeo de tipos de datos SQL -> Pyhton
            records = []
            grupo = None
            indice = None
            col = None
            tbl = None
            _tipo = None
            value = None
            for grupo in jsonData[elem['JSONGroupName']]:
                for tbl in grupo[elem['TableName']]:
                    record = []
                    for indice, col in enumerate(elem['ColumnList']):
                        dt = elem['DataType'][indice]
                        _tipo = ''.join([s for s in list(dt) if s.isalpha()])

                        value = tbl.get(col) if (
                            tbl.get(col, None) is not None) else ''

                        if(_tipo in {'bit', 'bigint', 'int', 'smallint', 'tinyint'} and value != ''):
                            value = int(value)

                        record.append(value)
                    records.append(record)
            return self.eliminarDuplicados(records)
        except Exception as e:
            _t = f"ERROR:{str(e)}.\n"
            if(grupo):
                _t += f"Grupo: {grupo}.\n"
            if(tbl):
                _t += f"Tabla: {tbl}.\n"
            if(col):
                _t += f"Columna: {col}.\n"
            if(_tipo):
                _t += f"_Tipo:{_tipo}.\n"
            if(value):
                _t += f"value:{value}.\n"
            logger.info(_t)

    def eliminarDuplicados(self, mylist: list) -> list:
        seen = set()
        newlist = []
        for item in mylist:
            t = tuple(item)
            if t not in seen:
                newlist.append(item)
                seen.add(t)
        return newlist

    def crearCSV(self, jsonFileName: str, fileName: str, TableName: str, columnList: list, unique_records: list):
        # https://pymotw.com/2/csv/
        try:
            csv.register_dialect('escaped', delimiter=self.args._sep, lineterminator='\n',
                                 skipinitialspace=0, escapechar=None, doublequote=True,
                                 quoting=csv.QUOTE_MINIMAL, quotechar='"')
            _c = len(unique_records)
            _f = open(fileName, 'w', encoding=self.args._encode)
            dialect = csv.get_dialect("escaped")
            writer = csv.writer(_f, dialect=dialect)
            writer.writerow(columnList)
            writer.writerows(unique_records)
            _t = f"Table {TableName} -> {_c} registros procesados."
            _f.close()
        except Exception as e:
            _t = f"ERROR:'{str(e)}'. Tabla:'{TableName}'. #Registros: '{_c}'"
        finally:
            logger.info(_t)
        return True
