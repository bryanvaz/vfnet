############################################################
#
# Table Formatting Library
#
# Author: Bryan Vaz <bryan@bryanvaz.com>
# Date Created: 2020-05-24
# Last Modified: 2020-05-24
#
# Formats the output of a table to be printed 
# to the console.
#
# Copyright (c) 2023 Bryan Vaz.
#
# This file is part of vfnet.
#
# vfnet is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation,
# either version 3 of the License, or (at your option) any
# later version.
#
# vfnet is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public
# License along with vfnet. If not, see
# <https://www.gnu.org/licenses/>.
#
############################################################

from typing import List, Dict, Union, Any

def print_table(data: List[Dict[str, Any]], keys: List[str], headers: List[str], sort_columns: Union[List[str],str] = []) -> None:
    """
    Prints a formatted table based on the provided data, keys, headers, and optional sort column.

    Args:
        data (List[Dict[str, Any]]): The data to be displayed in the table as a list of dictionaries.
        keys (List[str]): The keys from the dictionaries representing the columns of the table.
        headers (List[str]): The headers for each column of the table.
        sort_column (str, optional): The column to sort the table by. Defaults to None.
    """

    if isinstance(sort_columns, str):
        sort_columns = [sort_columns]


    # Calculate the maximum lengths for each column based on the headers and data
    column_lengths = [len(header) for header in headers]

    for row in data:
        values = [str(row[column]) for column in keys]
        column_lengths = [max(length, len(value)) for length, value in zip(column_lengths, values)]

    # Sort the data if a sort column is specified
    # if sort_column is not None:
    #     data.sort(key=lambda row: row[sort_column])
    if sort_columns:
        data.sort(key=lambda row: tuple(row[column] for column in sort_columns))

    # Print the table headers
    print("  ".join([header.ljust(length + 1) for header, length in zip(headers, column_lengths)]))

    # Print the separator line
    print("  ".join(["=" * (length + 1) for length in column_lengths]))

    # Print the table rows
    for row in data:
        values = [str(row[column]).ljust(length + 1) for column, length in zip(keys, column_lengths)]
        print("  ".join(values))
