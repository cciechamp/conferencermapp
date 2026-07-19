from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

db = SQLAlchemy()

def create_app():
    """Build and configure the Flask application (the app factory).

    Configures the SQLite database URI (``db/bookings.db``), initializes the
    SQLAlchemy extension, registers the ``bookings`` and ``rooms`` blueprints,
    defines the ``/health`` route, and creates any missing tables.

    Args:
        None. Configuration is hard-coded/derived from the module location.

    Returns:
        flask.Flask: A fully configured application instance, ready to be run
        with ``app.run()`` or served by a WSGI server.

    Examples:
        Example 1 — create an app and serve it:

        >>> app = create_app()
        >>> app.run(debug=True)  # doctest: +SKIP

        Example 2 — create an app and drive it with the test client:

        >>> app = create_app()
        >>> client = app.test_client()
        >>> client.get("/health").get_json()["status"]
        'ok'

    Browser:
        Not an HTTP endpoint. Once the returned app is running, hit any route,
        e.g. http://localhost:5000/health

    cURL:
        curl http://localhost:5000/health
    """
    app = Flask(__name__)
    base_dir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(base_dir, 'db', 'bookings.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'workshop-secret-key'

    db.init_app(app)

    from routes.bookings import bookings_bp
    from routes.rooms import rooms_bp
    app.register_blueprint(bookings_bp)
    app.register_blueprint(rooms_bp)

    @app.route('/health')
    def health():
        """Report service liveness.

        A lightweight endpoint (no database access) for uptime checks and
        load-balancer probes.

        Route:
            GET /health

        Args:
            None. Takes no path or query parameters.

        Returns:
            dict: ``{"status": "ok", "service": "conference-room-booking"}``.
            Flask serializes the dict to a JSON response with HTTP status 200.

        Examples:
            Example 1 — check liveness in Python:

            >>> import requests
            >>> requests.get("http://localhost:5000/health").json()["status"]
            'ok'

            Example 2 — assert the service is up before running a test suite:

            >>> import requests
            >>> assert requests.get("http://localhost:5000/health").status_code == 200

        Browser:
            http://localhost:5000/health

        cURL:
            curl http://localhost:5000/health
        """
        return {'status': 'ok', 'service': 'conference-room-booking'}

    with app.app_context():
        db.create_all()

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
