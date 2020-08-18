import os
import json

from vee.git import GitRepo


class DevPackage(GitRepo):
    
    def __init__(self, db_row, home):
        super(DevPackage, self).__init__(
            work_tree=db_row['path'],
            # remote_name=db_row['remote'],
            # branch_name=db_row['branch'],
        )
        self.id = db_row.get('id')
        self.name = db_row['name']

        self.environ = db_row.get('environ') or {}
        if self.environ and isinstance(self.environ, str):
            self.environ = json.loads(self.environ)

        self.home = home

    def save_tag(self):
        tag_path = os.path.abspath(os.path.join(self.work_tree, '..', '.%s.vee-dev.json' % self.name))
        with open(tag_path, 'w') as fh:
            fh.write(json.dumps({
                'id': self.id,
                'name': self.name,
                'path': self.work_tree,
                'environ': self.environ,
            }))

    @classmethod
    def from_tag(cls, path, home=None):
        data = json.loads(open(path).read())
        data['id'] = None
        return cls(data, home=home)
