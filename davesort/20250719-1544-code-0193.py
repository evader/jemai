@socketio.on('request_jobs_list')
    def request_jobs_list():
        """
        Sends the current list of jobs to the client.
        """
        emit('jobs_list_update', jobs)