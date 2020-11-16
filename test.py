import json
import h5py
import numpy as np


person_dict = {'type': 'polygon',
'coords': [[0,0] for i in range(100)],
'label': 'color'
}
# with open('person.json', 'w') as json_file:
#     json.dump(person_dict, json_file)

# with h5py.File("person.hdf5", "w") as f:
#     anno = f.require_group('/annotations/1')
#     anno.attrs['type'] = 'polygon'
#     anno.attrs['label'] = 'color'
#     f.create_dataset('coords', shape=(100,2), data=np.array(person_dict['coords']))

import time

s = time.time()

for i in range(1000):
    with open('person.json') as f:
        data = json.load(f)
        a = data['type']
        a = np.array(data['coords'])

print(data)
print(time.time() - s)


# for i in range(1000):
#     with h5py.File("person.hdf5", 'a') as f:
#         anno = f['/annotations/1']
#         a = anno.attrs['type']
#         a = np.array(f['coords'])
# print(time.time() - s)