# Third-party notices

Housemate is MIT-licensed ([LICENSE](LICENSE)). It builds on, and in places
reuses, the work below.

## Studio Code Server (hassio-addons/app-vscode)

Housemate's add-on reuses patterns from
[Studio Code Server](https://github.com/hassio-addons/app-vscode): running
code-server behind Ingress with authentication left to Home Assistant, the
`s6-overlay` service layout (an init oneshot ahead of a long-running
code-server service that takes the container down when it stops), the
code-server flags and first-start settings, and the Dockerfile's way of
installing a pinned code-server release and an extension into its extensions
directory. Its licence, with its copyright notice:

    # MIT License
    
    Copyright (c) 2019-2026 Franck Nijhof
    
    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:
    
    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.
    
    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.

## Matt Pocock's skills (mattpocock/skills)

The engineering skills in the kit (`tdd`, `diagnosing-bugs`, `codebase-design`,
`domain-modeling`, `grilling`) and the commands made from the steps only a user
should start (`/grill`, `/to-spec`, `/to-tickets`, `/triage`,
`/setup-matt-pocock-skills`) are copied from
[mattpocock/skills](https://github.com/mattpocock/skills), at the commit pinned
as `MATT_SKILLS_REVISION` in `housemate_edge/Dockerfile`, and adapted for
OpenCode and for the local tracker (`housemate_edge/build/vendor_skills.py`).
The kit's `code-review` and `writing-for-agents` skills began as the maintainer's
own, themselves adapted from the same repository, and are made generic; the same
notice covers them.
They are copied into the user's `/config` with the licence below, which is also
kept in `.opencode/support/mattpocock-skills/LICENSE` there. Its licence, with
its copyright notice:

    MIT License

    Copyright (c) 2026 Matt Pocock

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.

## Pinned into the image, not copied

These are downloaded at build time from their releases, pinned by version and
checksum, and keep their own licences.

- [OpenCode](https://github.com/anomalyco/opencode), MIT, copyright the
  OpenCode authors.
- [code-server](https://github.com/coder/code-server), MIT, copyright Coder
  Technologies Inc.
- [OpenCode's editor extension](https://open-vsx.org/extension/sst-dev/opencode)
  (`sst-dev.opencode`), MIT.
- The [hassio-addons Debian base image](https://github.com/hassio-addons/addon-debian-base),
  MIT, and Debian's packages under their own licences.
