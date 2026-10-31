# Housemate (edge): code-server behind Ingress, with OpenCode in its terminal.
# Built the way Home Assistant now builds apps: this file is the whole recipe,
# the base is a multi-arch image, and CI supplies BUILD_ARCH (amd64|aarch64).
#
# To update OpenCode or code-server: Renovate changes the version, a workflow
# recomputes the checksums (.github/scripts/pin_checksums.py), and the publish
# workflow bumps the add-on's version and changelog on merge. By hand, run
# pin_checksums.py after changing a version; do not edit `version` in
# config.yaml. Neither updates itself at runtime. See docs/update-pipeline.md.

# hassio-addons Debian base, by tag and index digest. Renovate reads this line
# (renovate.json, customManagers); keep its shape.
ARG BUILD_FROM=ghcr.io/hassio-addons/debian-base:9.5.1@sha256:4e891c053f1a0205218fe801d7f187b2c6dc01eb7f4ead83b3033a6f22cf2869
# hadolint ignore=DL3006
FROM ${BUILD_FROM}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# OpenCode https://github.com/anomalyco/opencode/releases (MIT). The x64
# *baseline* build, because the regular one needs AVX2 and a Home Assistant
# guest may sit on a baseline virtual CPU.
# renovate: datasource=github-releases depName=anomalyco/opencode extractVersion=^v(?<version>.+)$
ARG OPENCODE_VERSION=2.2.5
ARG OPENCODE_SHA256_AMD64=09f44302c10fd036912f59c81fd1aef5df45dd06f649197f9dfc9bbe2a79614e
ARG OPENCODE_SHA256_AARCH64=5a528f42caf576c6cdece6a191eb273d3db54effa5518e0402684d8f8026aeb6

# code-server https://github.com/coder/code-server/releases (MIT).
# renovate: datasource=github-releases depName=coder/code-server extractVersion=^v(?<version>.+)$
ARG CODE_SERVER_VERSION=4.144.0
ARG CODE_SERVER_SHA256_AMD64=710f749c40a0f3d0ab3be09c0de65314e5c2907cc50646f5fbc0f24c0e8fba2d
ARG CODE_SERVER_SHA256_AARCH64=4404c784f541bd56a2a8d6e2a9474ed0b4e37bc8502aa3a247898ca933434482

# OpenCode's editor extension, from Open VSX (MIT).
ARG OPENCODE_EXTENSION_VERSION=1.0.0
ARG OPENCODE_EXTENSION_SHA256=ddec815ab9a4a481b351e1ea297996688a443d9ac02cb21b7d9b423ce315e0c4

ARG BUILD_ARCH
RUN \
    case "${BUILD_ARCH}" in \
        amd64) \
            opencode_asset="opencode-linux-x64-baseline.tar.gz"; \
            opencode_sha="${OPENCODE_SHA256_AMD64}"; \
            code_asset="code-server-${CODE_SERVER_VERSION}-linux-amd64.tar.gz"; \
            code_sha="${CODE_SERVER_SHA256_AMD64}"; \
            ;; \
        aarch64) \
            opencode_asset="opencode-linux-arm64.tar.gz"; \
            opencode_sha="${OPENCODE_SHA256_AARCH64}"; \
            code_asset="code-server-${CODE_SERVER_VERSION}-linux-arm64.tar.gz"; \
            code_sha="${CODE_SERVER_SHA256_AARCH64}"; \
            ;; \
        *) echo "Unsupported BUILD_ARCH: '${BUILD_ARCH}'" >&2; exit 1 ;; \
    esac \
    \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        git=1:2.47.3-0+deb13u1 \
        less=668-1 \
        nginx=1.26.3-3+deb13u10 \
        nginx-common=1.26.3-3+deb13u10 \
        openssh-client=1:10.0p1-7+deb13u4 \
        python3=3.13.5-1 \
        python3-minimal=3.13.5-1 \
        python3.13=3.13.5-2+deb13u5 \
        python3.13-minimal=3.13.5-2+deb13u5 \
        libpython3-stdlib=3.13.5-1 \
        libpython3.13-stdlib=3.13.5-2+deb13u5 \
        libpython3.13-minimal=3.13.5-2+deb13u5 \
        tmux=3.5a-3 \
        unzip=6.0-29+deb13u1 \
    \
    && curl -fsSL --retry 5 -o /tmp/opencode.tar.gz \
        "https://github.com/anomalyco/opencode/releases/download/v${OPENCODE_VERSION}/${opencode_asset}" \
    && echo "${opencode_sha}  /tmp/opencode.tar.gz" | sha256sum -c - \
    && tar -xzf /tmp/opencode.tar.gz -C /usr/local/bin opencode \
    && chmod 0755 /usr/local/bin/opencode \
    \
    && curl -fsSL --retry 5 -o /tmp/code-server.tar.gz \
        "https://github.com/coder/code-server/releases/download/v${CODE_SERVER_VERSION}/${code_asset}" \
    && echo "${code_sha}  /tmp/code-server.tar.gz" | sha256sum -c - \
    && mkdir -p /usr/local/lib/code-server \
    && tar -xzf /tmp/code-server.tar.gz --strip-components=1 -C /usr/local/lib/code-server \
    && ln -s /usr/local/lib/code-server/bin/code-server /usr/local/bin/code-server \
    \
    && curl -fsSL --retry 5 -o /tmp/opencode.vsix \
        "https://open-vsx.org/api/sst-dev/opencode/${OPENCODE_EXTENSION_VERSION}/file/sst-dev.opencode-${OPENCODE_EXTENSION_VERSION}.vsix" \
    && echo "${OPENCODE_EXTENSION_SHA256}  /tmp/opencode.vsix" | sha256sum -c - \
    && ext_dir="/usr/local/lib/code-server/lib/vscode/extensions/sst-dev.opencode-${OPENCODE_EXTENSION_VERSION}" \
    && mkdir -p /tmp/vsix "${ext_dir}" \
    && unzip -q /tmp/opencode.vsix -d /tmp/vsix \
    && cp -a /tmp/vsix/extension/. "${ext_dir}/" \
    \
    && apt-get purge -y --auto-remove unzip \
    && rm -rf /tmp/* /var/lib/apt/lists/* /var/cache/* /var/log/*

# Where the add-on keeps its state. Everything below /data survives restarts
# and updates. These are set in the services too; here so that a shell opened
# any other way (docker exec, an s6 oneshot) sees the same places.
ENV \
    XDG_CONFIG_HOME=/data/opencode/config \
    XDG_DATA_HOME=/data/opencode/data \
    XDG_STATE_HOME=/data/opencode/state \
    XDG_CACHE_HOME=/data/opencode/cache \
    OPENCODE_DISABLE_AUTOUPDATE=true \
    OPENCODE_ENABLE_QUESTION_TOOL=true

COPY rootfs /

# Matt Pocock's engineering skills https://github.com/mattpocock/skills (MIT),
# pinned by commit and made into the kit's baseline skills and commands by
# build/vendor_skills.py (user-invoked steps become OpenCode commands). Renovate
# bumps the commit; the build stops if upstream changes which steps are
# user-invoked. Only the commit is checked out, and the fetch refuses a commit
# that is not the one named.
# renovate: git-refs https://github.com/mattpocock/skills main
ARG MATT_SKILLS_REVISION=a496f5513d4a4cf889bc48e189e579f4b0bdf6aa
COPY build/vendor_skills.py /tmp/vendor_skills.py
RUN \
    git init -q /tmp/skills \
    && git -C /tmp/skills fetch -q --depth 1 https://github.com/mattpocock/skills.git "${MATT_SKILLS_REVISION}" \
    && git -C /tmp/skills checkout -q FETCH_HEAD \
    && test "$(git -C /tmp/skills rev-parse HEAD)" = "${MATT_SKILLS_REVISION}" \
    && python3 -I /tmp/vendor_skills.py /tmp/skills /usr/share/housemate/kit --revision "${MATT_SKILLS_REVISION}" \
    && rm -rf /tmp/*

# code-server's health endpoint, asked through nginx on the Ingress port, so that
# it checks both.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s \
    CMD curl --fail --silent http://127.0.0.1:1337/healthz || exit 1

ARG BUILD_VERSION
LABEL \
    io.hass.name="Housemate (edge)" \
    io.hass.description="An agent in the sidebar that builds Home Assistant with you" \
    io.hass.type="addon" \
    io.hass.version="${BUILD_VERSION}" \
    org.opencontainers.image.title="Housemate (edge)" \
    org.opencontainers.image.description="An agent in the sidebar that builds Home Assistant with you" \
    org.opencontainers.image.licenses="MIT" \
    org.opencontainers.image.source="https://github.com/jceccato/housemate" \
    org.opencontainers.image.version="${BUILD_VERSION}"
