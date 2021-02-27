import socket

class MailServer:

    def __init__(self, port: int = 65000):

        # create socket with tcp capabitlities (IP and TCP)
        self.skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # set additional configuration to the socket. Here we add
        # the capability to reuse the port when the port closes
        # without this we would need to wait for a timeout when the
        # socket closes (sucks for debugging)

        # SOL_SOCKET means the configuration we are setting are
        # protocol independent.
        self.skt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR | socket.SO_REUSEPORT )

        # bind the socket to a port, so it can listen for connections
        # going for it
        self.skt.bind(( self.skt.gethostname(), port ))

        # size of unattended connections queue, from this point on the
        # server is working
        self.skt.listen(5)

        self.serve_clients()

    def serve_clients(self):

        # clients can disconnect, but the server never dies
        while(True):

            # accept new client. Since we didn't specify otherwise,
            # the program will hang here until somebody connects
            (self.client_skt, self.client_addr) = self.skt.accept()

            # get their commands and respond to them...

            # * pegar username com HELO
            # * pegar recipiente/destinatario com RCPT/MAIL
            # * enviar emails para database com DATA
            # * responder OK para NOOP
            # * abortar conexão imediatamente com RSET
            # * fechar conexao com QUIT (mandar OK antes)

            # 4 first bytes tell us the command given
            command = client_skt.recv(4).decode("ascii").upper() # NOTE: commands are case insensitive

            if( command == "HELO" ):
                self.helo()
            elif( command == "MAIL"):
                self.mail()
            elif( command == "RCPT" ):
                self.rcpt()
            elif( command == "DATA" ):
                self.data()
            elif( command == "RSET" ):
                self.rset()
            elif( command == "NOOP" ):
                self.noop()
            elif( command == "QUIT" ):
                self.quit()

    def helo(self):
        pass
    def mail(self):
        pass
    def rcpt(self):
        pass
    def data(self):
        pass
    def rset(self):
        pass
    def noop(self):
        pass
    def quit(self):
        pass
