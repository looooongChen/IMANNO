class Table(object):

    def __init__(self):
        self.table = {}

    def __setitem__(self, key, item):
        self.table[key] = item

    def __getitem__(self, key):
        return self.table[key]
    
    def __delitem__(self, key):
        del self.table[key]

    def keys(self):
        return self.table.keys()
    
    def items(self):
        return self.table.items()
    
    def clear(self):
        self.table.clear()

    def pop(self, *args):
        return self.table.pop(*args)

    def __iter__(self):
        return iter(self.table)
    
    def __str__(self):
        return self.table.__str__()
