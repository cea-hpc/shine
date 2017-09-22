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
python setup.py install -O1 --skip-build --root %{buildroot} --record INSTALLED_FILES

# move 'shine' into /usr/sbin
mv %{buildroot}/usr/bin %{buildroot}/usr/sbin
sed -i 's#/usr/bin/shine#/usr/sbin/shine#' INSTALLED_FILES
# config files
install -d %{buildroot}/etc/shine/models
install -p -m 0644 conf/shine.conf %{buildroot}/etc/shine/
install -p -m 0644 conf/storage.conf %{buildroot}/etc/shine/
install -p -m 0644 conf/tuning.conf.example %{buildroot}/etc/shine/
install -p -m 0644 conf/models/example.lmf %{buildroot}/etc/shine/models/
# vim files
install -d %{buildroot}/%{vimdatadir}/{ftdetect,syntax}
install -p -m 0644 doc/extras/vim/ftdetect/shine.vim %{buildroot}/%{vimdatadir}/ftdetect/
install -p -m 0644 doc/extras/vim/syntax/shine.vim %{buildroot}/%{vimdatadir}/syntax/
install -p -m 0644 doc/extras/vim/syntax/shinefs.vim %{buildroot}/%{vimdatadir}/syntax/
# man pages
install -d %{buildroot}/%{_mandir}/{man1,man5}
install -p -m 0644 doc/shine.1 %{buildroot}/%{_mandir}/man1/
install -p -m 0644 doc/shine.conf.5 %{buildroot}/%{_mandir}/man5/

%files -f INSTALLED_FILES
%defattr(-,root,root)
%config(noreplace) %{_sysconfdir}/shine/*.conf
%config %{_sysconfdir}/shine/*.conf.example
%config %{_sysconfdir}/shine/models/*.lmf
%{vimdatadir}/ftdetect/*.vim
%{vimdatadir}/syntax/*.vim
%doc LICENSE README.md ChangeLog
%doc %{_mandir}/man1/shine.1*
%doc %{_mandir}/man5/shine.conf.5*

%changelog
* Wed May 24 2017 <aurelien.degremont@cea.fr> - 1.5-1
- Update to shine 1.5

* Wed Apr 29 2015 <aurelien.degremont@cea.fr> - 1.4-1
- Update to shine 1.4

* Tue Mar 11 2014 <aurelien.degremont@cea.fr> - 1.3.1-1
- Update to shine 1.3.1

* Thu Oct 10 2013 <aurelien.degremont@cea.fr> - 1.3-1
- Update to shine 1.3
