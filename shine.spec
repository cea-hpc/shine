%define vimdatadir %{_datadir}/vim/vimfiles

Name:      shine
Version:   1.5
Release:   1%{?dist}
Vendor:    CEA
License:   GPLv2+
Summary:   Lustre administration utility
Url:       https://github.com/cea-hpc/shine
Source0:   https://github.com/cea-hpc/shine/archive/v%{version}.tar.gz#/%{name}-%{version}.tar.gz
Group:     Development/Libraries
BuildArch: noarch
Requires:  clustershell >= 1.5.1

%description
Python-based Lustre utility to easily control Lustre filesystem
devices, mount points and routers.

%prep
%setup -q

%build
python setup.py build

%install
python setup.py install -O1 --skip-build --root %{buildroot}

# move 'shine' into /usr/sbin
mv %{buildroot}/usr/bin %{buildroot}/usr/sbin
# man pages
install -d %{buildroot}/%{_mandir}/{man1,man5}
install -p -m 0644 doc/shine.1 %{buildroot}/%{_mandir}/man1/
install -p -m 0644 doc/shine.conf.5 %{buildroot}/%{_mandir}/man5/

%files
%defattr(-,root,root)
%{_sysconfdir}/shine/*.conf.example
%config(noreplace) %{_sysconfdir}/shine/*.conf
%config(noreplace) %{_sysconfdir}/shine/models/*.lmf
%{_sbindir}/shine
%{python2_sitelib}/Shine/
%{python2_sitelib}/shine-*-py?.?.egg-info
%{vimdatadir}/ftdetect/*.vim
%{vimdatadir}/syntax/*.vim
%doc LICENSE README.md ChangeLog
%{_mandir}/man1/shine.1*
%{_mandir}/man5/shine.conf.5*
%{_usr}/share/shine/shine.init.redhat
%dir %{_localstatedir}/cache/shine/conf
%{_localstatedir}/cache/shine/conf/README

%changelog
* Wed May 24 2017 <aurelien.degremont@cea.fr> - 1.5-1
- Update to shine 1.5

* Wed Apr 29 2015 <aurelien.degremont@cea.fr> - 1.4-1
- Update to shine 1.4

* Tue Mar 11 2014 <aurelien.degremont@cea.fr> - 1.3.1-1
- Update to shine 1.3.1

* Thu Oct 10 2013 <aurelien.degremont@cea.fr> - 1.3-1
- Update to shine 1.3
