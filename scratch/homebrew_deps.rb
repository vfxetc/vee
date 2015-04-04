require 'json'

$:.unshift('/usr/local/Library/Homebrew')

require 'global'
require 'formula'


f = Formulary.factory('ffmpeg')

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

puts JSON.pretty_generate(info)


