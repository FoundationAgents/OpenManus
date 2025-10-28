// This file is auto-generated, don't edit it
import * as $dara from '@darabonba/typescript';


export class GetSessionResponseBodyData extends $dara.Model {
  appInstanceId?: string;
  resourceId?: string;
  sessionId?: string;
  success?: boolean;
  httpPort?: string;
  networkInterfaceIp?: string;
  token?: string;
  vpcResource?: boolean;
  resourceUrl?: string;
  static names(): { [key: string]: string } {
    return {
      appInstanceId: 'AppInstanceId',
      resourceId: 'ResourceId',
      sessionId: 'SessionId',
      success: 'Success',
      httpPort: 'HttpPort',
      networkInterfaceIp: 'NetworkInterfaceIp',
      token: 'Token',
      vpcResource: 'VpcResource',
      resourceUrl: 'ResourceUrl',
    };
  }

  static types(): { [key: string]: any } {
    return {
      appInstanceId: 'string',
      resourceId: 'string',
      sessionId: 'string',
      success: 'boolean',
      httpPort: 'string',
      networkInterfaceIp: 'string',
      token: 'string',
      vpcResource: 'boolean',
      resourceUrl: 'string',
    };
  }

  validate() {
    super.validate();
  }

  constructor(map?: { [key: string]: any }) {
    super(map);
  }
}

