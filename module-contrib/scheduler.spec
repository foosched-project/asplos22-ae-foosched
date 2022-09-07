# SPDX-License-Identifier: GPL-2.0 OR BSD-3-Clause

%define minor_name xxx
%define release yyy

Name:		scheduler-%{minor_name}
Version:	%{KVER}
Release:	%{KREL}.%{release}
Summary:	The schedule policy RPM for linux kernel scheduler subsystem
BuildRequires:	elfutils-devel
BuildRequires:	systemd
Requires:	systemd
Requires:	binutils
Requires:	cpio

Group:		System Environment/Kernel
License:	GPLv2
URL:		None

%description
The scheduler policy rpm-package.

%prep
# copy files to rpmbuild/SOURCE/
cp %{_outdir}/* %{_sourcedir}
cp %{_tmpdir}/boundary.yaml %{_sourcedir}

chmod 0644 %{_sourcedir}/{version,boundary.yaml}
rm -f %{_sourcedir}/scheduler.spec

%build
# Build sched_mod
make KBUILD_MODPOST_WARN=1 foosched_tmpdir=%{_tmpdir} foosched_modpath=%{_modpath} \
	sidecar_objs=%{_sdcrobjs} -C %{_kerneldir} -f %{_tmpdir}/Makefile.foosched \
	foosched -j %{threads}

# Build symbol resolve tool
make -C %{_tmpdir}/symbol_resolve

# Generate the tainted_functions file
awk -F '[(,)]' '$2!=""{print $2" "$3" vmlinux"}' %{_modpath}/tainted_functions.h > %{_sourcedir}/tainted_functions
chmod 0444 %{_sourcedir}/tainted_functions

%install
#install tool, module and systemd service
mkdir -p %{buildroot}/usr/lib/systemd/system
mkdir -p %{buildroot}%{_localstatedir}/foosched/%{KVER}-%{KREL}.%{_arch}

install -m 755 %{_tmpdir}/symbol_resolve/symbol_resolve %{buildroot}%{_localstatedir}/foosched/%{KVER}-%{KREL}.%{_arch}/symbol_resolve
install -m 755 %{_modpath}/scheduler.ko %{buildroot}%{_localstatedir}/foosched/%{KVER}-%{KREL}.%{_arch}/scheduler.ko
install -m 644 %{_sourcedir}/foosched.service %{buildroot}/usr/lib/systemd/system

cp %{_sourcedir}/* %{buildroot}%{_localstatedir}/foosched/%{KVER}-%{KREL}.%{_arch}
rm -f %{buildroot}%{_localstatedir}/foosched/%{KVER}-%{KREL}.%{_arch}/foosched.service

#install kernel module after install this rpm-package
%post
sync

if [ "$(uname -r)" != "%{KVER}-%{KREL}.%{_arch}" ]; then
	echo "INFO: scheduler does not match current kernel version, skip starting service ..."
	exit 0
fi

echo "Start foosched.service"
systemctl enable foosched
systemctl start foosched

#uninstall kernel module before remove this rpm-package
%preun
if [ "$(uname -r)" != "%{KVER}-%{KREL}.%{_arch}" ]; then
	echo "INFO: scheduler does not match current kernel version, skip unloading module..."
	exit 0
fi

echo "Stop foosched.service"
/var/foosched/$(uname -r)/scheduler-installer uninstall || exit 1
systemctl stop foosched

%postun
systemctl reset-failed foosched

%files
/usr/lib/systemd/system/foosched.service
%{_localstatedir}/foosched/%{KVER}-%{KREL}.%{_arch}/*

%dir
%{_localstatedir}/foosched/%{KVER}-%{KREL}.%{_arch}

%changelog
