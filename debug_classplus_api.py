from extractors.classplus_api import ClassplusClient
import json

c = ClassplusClient('dqxkl')
c.token = 'eyJhbGciOiJIUzM4NCIsInR5cCI6IkpXVCJ9.eyJpZCI6MTU0Njc1ODkwLCJvcmdJZCI6NTAxMywidHlwZSI6MSwibW9iaWxlIjoiOTE4NjI0OTIyOTQwIiwibmFtZSI6IkFycGl0IEFycGl0IiwiZW1haWwiOiJhcnBpdHBhdGlsNDY2QGdtYWlsLmNvbSIsImlzSW50ZXJuYXRpb25hbCI6MCwiZGVmYXVsdExhbmd1YWdlIjoiRU4iLCJjb3VudHJ5Q29kZSI6IklOIiwiY291bnRyeUlTTyI6IjkxIiwidGltZXpvbmUiOiJHTVQrNTozMCIsImlzRGl5Ijp0cnVlLCJvcmdDb2RlIjoiZHF4a2wiLCJpc0RpeVN1YmFkbWluIjowLCJmaW5nZXJwcmludElkIjoiMDk3N2QxNzIwZDU5YWEzMmRkOWU2ODA5YzVlNjEzOGRmYjM5ZjBiMDYyMTc3NjIxYTNkODAwMjQwMDY4ZWM4ZSIsImlhdCI6MTc4MDkzMjM5NCwiZXhwIjoxNzgxNTM3MTk0fQ.OldLy51QjElqLbRx-qt3_kw05Jwavxcz2zHayMgkDdLE56Uuoke8jRNZQ3Ul2t_e'
c.headers['x-access-token'] = c.token

courses = c.fetch_courses()
print('Courses:', courses)

if courses.get('success'):
    course_list = courses.get('data', {}).get('data', {}).get('courses', [])
    for course in course_list:
        course_id = course.get('id')
        print('Found course id:', course_id)
        
        res = c.session.get(f'https://api.classplusapp.com/v2/course/content/get?courseId={course_id}', headers=c.headers)
        print('Course content status:', res.status_code)
        print('Set-Cookie:', res.headers.get('Set-Cookie'))
        break
