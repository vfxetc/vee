from vee.git import GitRepo


class DevPackage(GitRepo):
    
    def __init__(self, db_row, home):
        super(DevPackage, self).__init__(
            work_tree=db_row['path'],
            # remote_name=db_row['remote'],
            # branch_name=db_row['branch'],
        )
        self.id = db_row['id']
        self.name = db_row['name']
        self.home = home

