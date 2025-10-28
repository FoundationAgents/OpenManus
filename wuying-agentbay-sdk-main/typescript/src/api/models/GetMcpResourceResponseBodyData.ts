// This file is auto-generated, don't edit it
import * as $dara from '@darabonba/typescript';
import { GetMcpResourceResponseBodyDataDesktopInfo } from "./GetMcpResourceResponseBodyDataDesktopInfo";


export class GetMcpResourceResponseBodyData extends $dara.Model {
  desktopInfo?: GetMcpResourceResponseBodyDataDesktopInfo;
  resourceUrl?: string;
  sessionId?: string;
  static names(): { [key: string]: string } {
    return {
      desktopInfo: 'DesktopInfo',
      resourceUrl: 'ResourceUrl',
      sessionId: 'SessionId',
    };
  }

  static types(): { [key: string]: any } {
    return {
      desktopInfo: GetMcpResourceResponseBodyDataDesktopInfo,
      resourceUrl: 'string',
      sessionId: 'string',
    };
  }

  validate() {
    if(this.desktopInfo && typeof (this.desktopInfo as any).validate === 'function') {
      (this.desktopInfo as any).validate();
    }
    super.validate();
  }

  constructor(map?: { [key: string]: any }) {
    super(map);
  }
}

