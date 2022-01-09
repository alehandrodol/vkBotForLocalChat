from typing import Any
from json import dumps, loads


def add_new_column_in_json(ind: int):
    res = ""
    with open("DataBases/users_data.json", "r") as f:
        read = f.read()
        data_list: list[list] = loads(read)['values']
        new_list = []
        for ind1, record in enumerate(data_list):
            temp = record
            temp.insert(ind, temp[4]*100 + temp[5]*50)
            new_list.insert(ind1, temp)
        res_dict = {'values': new_list}
        res = dumps(res_dict, ensure_ascii=False)

    with open("DataBases/users_data.json", "w") as f:
        f.write(res)


if __name__ == "__main__":
    pass  # add_new_column_in_json(6)
