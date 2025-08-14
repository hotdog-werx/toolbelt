# This file needs trailing commas added (multi-line structures for add-trailing-comma test)
# Modified to ensure add-trailing-comma introduces changes (multi-line params & literals)
def function_with_args(
    arg1,
    arg2,
    arg3
):
    data = {
        'key1': 'value1',
        'key2': 'value2',
        'key3': 'value3'
    }

    my_list = [
        'item1',
        'item2',
        'item3'
    ]

    return data, my_list
