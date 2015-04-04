import subprocess
import os
import json
from pprint import pprint

r_fd, child_wfd = os.pipe()
child_rfd, w_fd = os.pipe()

proc = subprocess.Popen(['ruby'], stdin=subprocess.PIPE, bufsize=0)

proc.stdin.write('''

require 'json'

$:.unshift('/usr/local/Library/Homebrew')
require 'global'
require 'formula'

r_fh = IO.new(%(child_rfd)s, 'r')
w_fh = IO.new(%(child_wfd)s, 'w')

w_fh.write("HELLO\\n")
w_fh.flush

while true do

    raw = r_fh.readline
    if !raw then 
        break
    end
    num = raw.to_i
    cmd = r_fh.read(num)

    begin
        res = JSON.generate({:result => eval(cmd)})
    rescue => e
        res = JSON.generate({:error => e.to_s})
    end

    w_fh.write(res.length.to_s + ' ')
    w_fh.write(res)
    w_fh.flush

end

''' % globals())
proc.stdin.close()

assert os.read(r_fd, 6) == "HELLO\n"
os.close(child_wfd)
os.close(child_rfd)


def run(source):

    os.write(w_fd, '%d\n' % len(source))
    os.write(w_fd, source)

    len_buffer = []
    while True:
        c = os.read(r_fd, 1)
        if not c:
            raise RuntimeError('pipe closed')
        if c == ' ':
            break
        len_buffer.append(c)
    len_ = int(''.join(len_buffer))

    raw_response = os.read(r_fd, len_)
    response = json.loads(raw_response)
    if 'error' in response:
        raise ValueError(response['error'])
    else:
        return response['result']


run('''

def get_info(name)

    f = Formulary.factory(name, :stable)

    info = f.to_hash
    info['dependencies'] = deps = {}

    f.deps.each {|dep|

        dep_class   = 'build' if dep.build?
        dep_class ||= 'optional' if dep.optional?
        dep_class ||= 'required'

        deps[dep.to_s] = {
            :class => dep_class,
            :installed => (dep.to_formula.version if dep.installed?),
        }

    }

    info

end

''')


for name in 'oath-toolkit', 'wget', 'x264':
    pprint(run('get_info(%r)' % name))
    print

     
