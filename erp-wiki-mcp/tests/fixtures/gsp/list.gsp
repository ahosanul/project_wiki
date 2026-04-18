<!DOCTYPE html>
<html xmlns:g="http://grails.org/tag/gsp">
<head>
    <meta name="layout" content="main"/>
    <title>User List</title>
</head>
<body>
    <div class="container">
        <h1>Users</h1>
        
        <g:if test="${flash.message}">
            <div class="alert alert-info">${flash.message}</div>
        </g:if>
        
        <table class="table">
            <thead>
                <tr>
                    <th>Email</th>
                    <th>Username</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                <g:each in="${users}" var="user">
                    <tr>
                        <td>${user.email}</td>
                        <td>${user.username}</td>
                        <td>
                            <g:link action="show" id="${user.id}">View</g:link>
                            <g:link action="edit" id="${user.id}">Edit</g:link>
                            <g:link action="delete" id="${user.id}" method="DELETE">Delete</g:link>
                        </td>
                    </tr>
                </g:each>
            </tbody>
        </table>
        
        <g:link action="create" class="btn btn-primary">New User</g:link>
    </div>
</body>
</html>
