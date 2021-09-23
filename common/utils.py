def print_execution_func(func):
    f_name = func.__name__

    def wrapper(*args, **kwargs):
        print('Start "{}" function'.format(f_name))

        res = func(*args, **kwargs)

        print('Function "{}" is done'.format(f_name))

        return res
    return wrapper
