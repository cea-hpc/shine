
Name:      shine
Summary:   Lustre administration utility
Version:   1.5
Release:   1%{?dist}
Source0:   %{name}-%{version}.tar.gz
License:   GPL
Group:     Development/Libraries
BuildRoot: %{_tmppath}/%{name}-buildroot
BuildArch: noarch
Requires:  clustershell >= 1.5.1
Vendor:    CEA
Url:       https://github.com/cea-hpc/shine

%description
Lustre administration utility.

%prep
%setup -q

%build
python setup.py build

%install
python setup.py install -O1 --skip-build --root %{buildroot} --record INSTALLED_FILES
# move 'shine' into /usr/sbin
mv %{buildroot}/usr/bin %{buildroot}/usr/sbin
sed -i 's#/usr/bin/shine#/usr/sbin/shine#' INSTALLED_FILES
# man pages
mkdir -p %{buildroot}/%{_mandir}/{man1,man5}
gzip -c doc/shine.1 >%{buildroot}/%{_mandir}/man1/shine.1.gz
gzip -c doc/shine.conf.5 >%{buildroot}/%{_mandir}/man5/shine.conf.5.gz

%clean
rm -rf %{buildroot}

%files -f INSTALLED_FILES
%defattr(-,root,root)
%config(noreplace) %{_sysconfdir}/shine/*.conf
%config %{_sysconfdir}/shine/*.conf.example
%config %{_sysconfdir}/shine/models/*.lmf
%doc LICENSE README.md ChangeLog
%doc %{_mandir}/man1/shine.1.gz
%doc %{_mandir}/man5/shine.conf.5.gz

%changelog
* Wed May 24 2017 <aurelien.degremont@cea.fr> - 1.5-1
- Update to shine 1.5

* Wed Apr 29 2015 <aurelien.degremont@cea.fr> - 1.4-1
- Update to shine 1.4

* Tue Mar 11 2014 <aurelien.degremont@cea.fr> - 1.3.1-1
- Update to shine 1.3.1

* Thu Oct 10 2013 <aurelien.degremont@cea.fr> - 1.3-1
- Update to shine 1.3
