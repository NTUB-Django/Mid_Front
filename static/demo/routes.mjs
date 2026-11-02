export const PAGES = {
 '/':'dashboard', '/accounts/login/':'login', '/accounts/register/':'register',
 '/school/login/':'login', '/admin/login/':'login', '/accounts/logout/':'logout', '/school/logout/':'logout',
 '/courses/browse/':'browse', '/school/courses/':'school-browse',
 '/selection/timetable/':'timetable','/selection/timetable/print/':'print',
 '/selection/prelist/':'timetable','/selection/results/':'timetable',
 '/selection/import/excel/':'excel','/selection/calendar/':'calendar',
 '/selection/calendar/events/new/':'new-event','/accounts/profile/':'profile',
 '/accounts/connections/':'connections','/school/':'school','/admin/':'admin',
 '/school/classes/':'classes','/timetables/classes/':'classes',
 '/school/offerings/':'capacities','/selection/console/offerings/':'capacities',
 '/school/students/import/':'students','/accounts/roles/':'roles',
 '/selection/console/':'console','/demo/storage/':'storage'
};
export function resolveRoute(path) {
 path=path.endsWith('/')?path:path+'/';
 if(PAGES[path])return {page:PAGES[path]};
 const patterns=[
  [/^\/(?:courses\/offering|school\/offerings)\/(\d+)\/(roster\/)?$/,'course'],
  [/^\/selection\/timetable\/student\/([^/]+)\/$/,'shared'],
  [/^\/selection\/calendar\/events\/([^/]+)\/$/,'event'],
  [/^\/accounts\/profile\/([^/]+)\/$/,'member'],
  [/^\/accounts\/groups\/([^/]+)\/$/,'group']
 ];
 for(const [pattern,page] of patterns){const match=path.match(pattern);if(match)return {page,id:match[1],roster:!!match[2]};}
 return {page:'missing'};
}
