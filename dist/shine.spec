%define name shine
%define release 1.el5

Summary: Lustre shine administration utility
Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{name}-%{version}.tar.gz
License: GPL
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-buildroot
Prefix: %{_prefix}
BuildArchitectures: noarch
Requires: clustershell >= 1.1
Vendor: Stephane Thiell <stephane.thiell@cea.fr>
Url: http://lustre-shine.sourceforge.net/

%description
Lustre administration utility.

%prep
%setup

%build
python setup.py build

%install
python setup.py install --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES
mkdir -p $RPM_BUILD_ROOT/%{_sysconfdir}/shine/models
cp conf/*.conf* $RPM_BUILD_ROOT/%{_sysconfdir}/shine
cp conf/models/* $RPM_BUILD_ROOT/%{_sysconfdir}/shine/models

%clean
rm -rf $RPM_BUILD_ROOT

%files -f INSTALLED_FILES
%defattr(-,root,root)

%doc LICENSE README ChangeLog
%config %{_sysconfdir}/shine/*.conf
%config %{_sysconfdir}/shine/*.conf.example
%config %{_sysconfdir}/shine/models/*.lmf
